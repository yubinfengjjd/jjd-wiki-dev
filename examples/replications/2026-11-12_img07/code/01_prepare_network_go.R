#!/usr/bin/env Rscript
# img07 replica v2 — step 1: extract hub-gene network (from hdWGCNA modules/kME + saved TOM)
# and run real GO over-representation per module (clusterProfiler::enrichGO, offline org.Hs.eg.db).
# Usage:
#   Rscript 01_prepare_network_go.R --obj <hdWGCNA_object.rds> --tom <TOM.rda> --outdir <dir> \
#           [--wgcna_name tutorial] [--prefix INH_M] [--n_hubs 60] [--edge_rule within_between|topk] [--k_in 5] [--k_out 1] [--edges_per_node 6 (topk only)] [--go TRUE] \
#           [--orgdb org.Hs.eg.db] [--ont ALL] [--top_terms 5]
script_dir <- dirname(normalizePath(sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE)[1])))
source(file.path(script_dir, "argparse_lite.R"))
opt <- parse_cli(list(obj = NA, tom = NA, outdir = NA, wgcna_name = NA, prefix = "INH_M", n_hubs = 60,
                      edges_per_node = 6, k_in = 5, k_out = 1, edge_rule = "within_between", go = TRUE, orgdb = "org.Hs.eg.db", ont = "ALL", top_terms = 5,
                      min_gs = 10, max_gs = 500), required = c("obj", "outdir"))
dir.create(opt$outdir, recursive = TRUE, showWarnings = FALSE)
t0 <- Sys.time()
logf <- function(...) cat(format(Sys.time(), "[%H:%M:%S] "), ..., "\n", sep = "")
memf <- function(tag) { g <- gc(); logf(tag, " R mem used (Mb): ", round(sum(g[, 2]), 1)) }

suppressPackageStartupMessages({
  library(Seurat); library(hdWGCNA); library(dplyr)
})
logf("readRDS ", opt$obj)
obj <- readRDS(opt$obj)
wname <- if (is.na(opt$wgcna_name)) obj@misc$active_wgcna else opt$wgcna_name
logf("wgcna_name: ", wname)
mods <- GetModules(obj, wgcna_name = wname)
# TOM path recorded by hdWGCNA if not given
tom_path <- opt$tom
if (is.na(tom_path)) tom_path <- obj@misc[[wname]]$wgcna_net$TOMFiles
n_cells <- ncol(obj)
wgcna_genes <- GetWGCNAGenes(obj, wgcna_name = wname)  # gene order of datExpr == TOM row/col order (as hdWGCNA::GetTOM)
rm(obj); invisible(gc()); memf("after dropping Seurat object")

lev <- if (is.factor(mods$module)) levels(droplevels(mods$module)) else unique(as.character(mods$module))
mods$module <- as.character(mods$module)
# keep hdWGCNA module order as stored (factor levels if present), drop grey
mod_levels <- setdiff(lev, "grey")
mod_map <- data.frame(module = mod_levels,
                      module_name = paste0(opt$prefix, seq_along(mod_levels)),
                      wgcna_color = mod_levels, stringsAsFactors = FALSE)
write.table(mod_map, file.path(opt$outdir, "module_map.tsv"), sep = "\t", quote = FALSE, row.names = FALSE)
mods2 <- mods[mods$module != "grey", c("gene_name", "module")]
ri <- match(mods2$gene_name, mods$gene_name)
mods2$kME <- vapply(seq_along(ri), function(i) mods[[paste0("kME_", mods2$module[i])]][ri[i]], numeric(1))
mods2 <- merge(mods2, mod_map, by = "module")
write.table(mods2[order(mods2$module_name, -mods2$kME), c("gene_name", "module", "module_name", "kME")],
            file.path(opt$outdir, "module_genes_kME.tsv"), sep = "\t", quote = FALSE, row.names = FALSE)
logf("non-grey modules: ", length(mod_levels), "; genes: ", nrow(mods2))

# hub genes: top n_hubs by own-module kME
hubs <- mods2 %>% group_by(module_name) %>% arrange(desc(kME), .by_group = TRUE) %>%
  slice_head(n = opt$n_hubs) %>% ungroup() %>% as.data.frame()
write.table(hubs, file.path(opt$outdir, "hub_nodes.tsv"), sep = "\t", quote = FALSE, row.names = FALSE)

# TOM subset among hubs (loads full TOM once; ~1.4 GB for 13k genes)
logf("loading TOM ", tom_path); memf("before TOM")
env <- new.env(); load(tom_path, envir = env)
tom_name <- ls(env)[1]; TOM <- env[[tom_name]]; rm(env)
logf("TOM object '", tom_name, "' class ", paste(class(TOM), collapse = "/"))
n_tom <- if (inherits(TOM, "dist")) attr(TOM, "Size") else nrow(TOM)
if (n_tom != length(wgcna_genes)) stop("TOM size ", n_tom, " != number of WGCNA genes ", length(wgcna_genes))
idx <- match(hubs$gene_name, wgcna_genes)
if (anyNA(idx)) stop("hub genes missing from WGCNA gene list: ", sum(is.na(idx)))
if (inherits(TOM, "dist")) {
  # WGCNA saves TOM similarity as a 'dist' (lower triangle, column-wise); hdWGCNA::GetTOM does as.matrix().
  # Extract only the hub x hub block without materialising the 13k x 13k matrix.
  v <- unclass(TOM); attributes(v) <- NULL; rm(TOM)
  ii <- outer(idx, rep(1, length(idx))); jj <- t(ii)
  lo <- pmax(ii, jj); hi <- pmin(ii, jj)
  k_lin <- n_tom * (hi - 1) - hi * (hi - 1) / 2 + (lo - hi)
  sub <- matrix(0, length(idx), length(idx))
  off <- ii != jj
  sub[off] <- v[k_lin[off]]
  rm(v)
} else {
  sub <- as.matrix(TOM[idx, idx]); rm(TOM)
}
invisible(gc()); memf("after TOM subset")
dimnames(sub) <- list(hubs$gene_name, hubs$gene_name)
logf("hub TOM block: range ", paste(signif(range(sub[upper.tri(sub)]), 3), collapse = "-"),
     "; mean within-module ", signif(mean(sub[outer(hubs$module_name, hubs$module_name, "==") & upper.tri(sub)]), 3),
     "; mean between-module ", signif(mean(sub[outer(hubs$module_name, hubs$module_name, "!=") & upper.tri(sub)]), 3))
diag(sub) <- 0
# sparsify (v2). edge_rule = "within_between" (default): each node keeps its k_in strongest TOM neighbours
# inside its own module plus its k_out strongest TOM neighbours in other modules (union over nodes).
# edge_rule = "topk" reproduces v1 (top edges_per_node neighbours regardless of module).
# All kept edges carry their real TOM value; no edge is created that is not in the TOM block.
same_mod <- outer(hubs$module_name, hubs$module_name, "==")
keep <- matrix(FALSE, nrow(sub), ncol(sub))
for (i in seq_len(nrow(sub))) {
  if (opt$edge_rule == "topk") {
    keep[i, order(sub[i, ], decreasing = TRUE)[seq_len(opt$edges_per_node)]] <- TRUE
  } else {
    win <- which(same_mod[i, ] & seq_len(ncol(sub)) != i); btw <- which(!same_mod[i, ])
    if (length(win) && opt$k_in > 0) keep[i, win[order(sub[i, win], decreasing = TRUE)[seq_len(min(opt$k_in, length(win)))]]] <- TRUE
    if (length(btw) && opt$k_out > 0) keep[i, btw[order(sub[i, btw], decreasing = TRUE)[seq_len(min(opt$k_out, length(btw)))]]] <- TRUE
  }
}
keep <- keep | t(keep)
ij <- which(keep & upper.tri(keep), arr.ind = TRUE)
edges <- data.frame(from = rownames(sub)[ij[, 1]], to = colnames(sub)[ij[, 2]], TOM = sub[ij],
                    within_module = same_mod[ij])
logf("edge rule ", opt$edge_rule, ": ", nrow(edges), " edges; within-module fraction ", signif(mean(edges$within_module), 4))
# also save the module x module mean TOM among hubs (used to place module centres in the layout)
mm <- sapply(mod_map$module_name, function(a) sapply(mod_map$module_name, function(b) {
  x <- sub[hubs$module_name == a, hubs$module_name == b, drop = FALSE]; if (a == b) mean(x[upper.tri(x)]) else mean(x) }))
write.table(data.frame(module_name = rownames(mm), mm, check.names = FALSE), file.path(opt$outdir, "module_mean_tom.tsv"),
            sep = "\t", quote = FALSE, row.names = FALSE)
write.table(edges, file.path(opt$outdir, "hub_edges_tom.tsv"), sep = "\t", quote = FALSE, row.names = FALSE)
logf("hub nodes: ", nrow(hubs), "; edges: ", nrow(edges))

if (!isTRUE(opt$go)) { logf("GO skipped (--go FALSE; dev only)"); quit(status = 0) }
# GO over-representation per module (all module genes vs WGCNA gene universe)
suppressPackageStartupMessages({ library(clusterProfiler); library(opt$orgdb, character.only = TRUE) })
universe <- mods$gene_name
go_all <- list()
for (m in mod_map$module_name) {
  genes <- mods2$gene_name[mods2$module_name == m]
  ego <- tryCatch(enrichGO(gene = genes, universe = universe, OrgDb = get(opt$orgdb), keyType = "SYMBOL",
                           ont = opt$ont, pAdjustMethod = "BH", pvalueCutoff = 1, qvalueCutoff = 1,
                           minGSSize = opt$min_gs, maxGSSize = opt$max_gs, readable = FALSE),
                  error = function(e) { logf("enrichGO failed for ", m, ": ", conditionMessage(e)); NULL })
  if (is.null(ego) || nrow(as.data.frame(ego)) == 0) { logf(m, ": no GO result"); next }
  df <- as.data.frame(ego); df$module_name <- m; df$n_module_genes <- length(genes)
  go_all[[m]] <- df
  logf(m, " (", length(genes), " genes): ", nrow(df), " terms; top = ", df$Description[1], " p=", signif(df$pvalue[1], 3))
}
go <- do.call(rbind, go_all); rownames(go) <- NULL
go <- go[order(go$module_name, go$pvalue), ]
write.table(go, file.path(opt$outdir, "go_enrichment_all.tsv"), sep = "\t", quote = FALSE, row.names = FALSE)
top <- go %>% group_by(module_name) %>% arrange(pvalue, .by_group = TRUE) %>% slice_head(n = opt$top_terms) %>%
  ungroup() %>% mutate(neglog10p = -log10(pvalue)) %>% as.data.frame()
write.table(top, file.path(opt$outdir, "go_top_terms.tsv"), sep = "\t", quote = FALSE, row.names = FALSE)
writeLines(c(sprintf("n_cells_object\t%d", n_cells), sprintf("universe_genes\t%d", length(universe)),
             sprintf("tom_object\t%s", tom_name), sprintf("elapsed_s\t%.1f", as.numeric(difftime(Sys.time(), t0, units = "secs")))),
           file.path(opt$outdir, "prepare_summary.tsv"))
logf("done in ", round(as.numeric(difftime(Sys.time(), t0, units = "secs")), 1), " s")
