#!/usr/bin/env Rscript
# img07 replica v2 — step 2: hub-gene co-expression network (left) + linked per-module GO bar grid (right).
# Consumes only the tables written by 01_prepare_network_go.R; one palette drives nodes, labels,
# leader lines, facet strips and bars (jb style rules 1–4).
# Usage:
#   Rscript 02_plot_network_go.R --datadir <dir> --outdir <dir> [--palette palette.tsv]
#           [--width_px 3216] [--height_px 2160] [--dpi 300] [--ncol_bars 2] [--seed 42]
#           [--font "Liberation Sans"] [--stem replica]
script_dir <- dirname(normalizePath(sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE)[1])))
source(file.path(script_dir, "argparse_lite.R"))
opt <- parse_cli(list(datadir = NA, outdir = NA, palette = NA, width_px = 3216, height_px = 2160, dpi = 300,
                      ncol_bars = 2, seed = 42, x_cap = "auto", layout = "kk_modinit", within_boost = 3, init_spread = 1, font = "Liberation Sans", stem = "replica",
                      net_width = 2.0, bars_width = 1.0, label_wrap = 24, term_chars = 60, label_radius = 1.12, node_size = 1.5,
                      bar_text_mm = 1.76, strip_pt = 7.4, tick_pt = 5.8, xtitle_pt = 7.0, label_mm = 2.55, term_chars_capped = 40),
                 required = c("datadir", "outdir"))
suppressPackageStartupMessages({
  library(ggplot2); library(patchwork); library(igraph); library(ggrepel); library(dplyr)
  library(ragg); library(svglite)
})
dir.create(opt$outdir, recursive = TRUE, showWarnings = FALSE)
rd <- function(f) read.delim(file.path(opt$datadir, f), stringsAsFactors = FALSE, check.names = FALSE, quote = "")
nodes <- rd("hub_nodes.tsv"); edges <- rd("hub_edges_tom.tsv"); go <- rd("go_top_terms.tsv")
mod_map <- rd("module_map.tsv")
mods <- mod_map$module_name; n_mod <- length(mods)

# ---- palette: original img07 strip colours (sampled, see METHOD.md) then extension for n > 14 ----
pal_path <- if (is.na(opt$palette)) file.path(script_dir, "palette_img07.tsv") else opt$palette
pal_lines <- readLines(pal_path); pal_lines <- pal_lines[!grepl("^#", pal_lines)]
pal_tab <- read.delim(text = paste(pal_lines, collapse = "\n"), stringsAsFactors = FALSE, comment.char = "")
pal <- pal_tab$hex
if (n_mod > length(pal)) pal <- c(pal, grDevices::hcl.colors(n_mod - length(pal), "Dark 3"))
pal <- setNames(pal[seq_len(n_mod)], mods)
lighten <- function(col, a = 0.55) { m <- grDevices::col2rgb(col) / 255; grDevices::rgb(t(a * m + (1 - a))) }
ink_for <- function(col) { m <- grDevices::col2rgb(col); ifelse(0.299 * m[1, ] + 0.587 * m[2, ] + 0.114 * m[3, ] < 110, "white", "black") }

# ---- representative GO term per module (top by p) ----
title_case <- function(x) {
  small <- c("of", "to", "in", "via", "and", "or", "by", "for", "the", "a", "an", "on", "from", "with", "into")
  vapply(strsplit(x, " "), function(w) {
    out <- ifelse(tolower(w) %in% small, tolower(w), paste0(toupper(substring(w, 1, 1)), substring(w, 2)))
    out[1] <- paste0(toupper(substring(out[1], 1, 1)), substring(out[1], 2)); paste(out, collapse = " ")
  }, character(1))
}
go$term_tc <- title_case(go$Description)
go$bar_label <- paste0(go$term_tc, " (", go$ID, ")")
rep_term <- go %>% group_by(module_name) %>% slice_min(pvalue, n = 1, with_ties = FALSE) %>% ungroup()

# ---- network layout on TOM-weighted hub edges ----
# kk (default): Kamada–Kawai with edge length = 1 - TOM/max(TOM) + 0.05 (strong co-expression = short edge);
# fr: Fruchterman–Reingold with attraction weight TOM/max(TOM). Layout choice is presentational only.
# kk_modinit (v2 default): module centres from classical MDS of (1 - mean hub TOM between modules), nodes start
# at their module centre (+ N(0, init_spread) jitter), then Kamada–Kawai with edge length 1/(w'+0.05)/10 where
# w' = TOM/max(TOM) x within_boost for within-module edges (x1 otherwise). Boost only shortens drawn edges;
# edge set and TOM values are unchanged.
if (!"within_module" %in% names(edges)) edges$within_module <- nodes$module_name[match(edges$from, nodes$gene_name)] == nodes$module_name[match(edges$to, nodes$gene_name)]
g <- graph_from_data_frame(edges[, c("from", "to", "TOM", "within_module")], directed = FALSE,
                           vertices = nodes[, c("gene_name", "module_name", "kME")])
set.seed(opt$seed)
w <- E(g)$TOM / max(E(g)$TOM)
mods_v <- V(g)$module_name
lay <- switch(opt$layout,
  kk_modinit = {
    mm <- rd("module_mean_tom.tsv"); rownames(mm) <- mm$module_name; mm <- as.matrix(mm[, -1])
    dd <- 1 - mm / max(mm); diag(dd) <- 0
    cm <- stats::cmdscale(stats::as.dist(dd), k = 2); cm <- cm / max(abs(cm))
    init <- cm[mods_v, ] * 10 + matrix(stats::rnorm(2 * vcount(g), 0, opt$init_spread), ncol = 2)
    ww <- w * ifelse(as.logical(E(g)$within_module), opt$within_boost, 1)
    layout_with_kk(g, coords = init, weights = 1 / (ww + 0.05) / 10)
  },
  kk = layout_with_kk(g, weights = 1 - w + 0.05),
  fr = layout_with_fr(g, weights = w, niter = 2000),
  stop("unknown --layout ", opt$layout))
vd <- data.frame(gene = V(g)$name, module_name = V(g)$module_name, x = lay[, 1], y = lay[, 2])
el <- as_edgelist(g, names = FALSE)
ed <- data.frame(x = lay[el[, 1], 1], y = lay[el[, 1], 2], xend = lay[el[, 2], 1], yend = lay[el[, 2], 2])
ctr <- c(mean(range(vd$x)), mean(range(vd$y)))
cen <- vd %>% group_by(module_name) %>% summarise(cx = median(x), cy = median(y), .groups = "drop") %>%
  left_join(rep_term[, c("module_name", "term_tc")], by = "module_name")
span <- max(diff(range(vd$x)), diff(range(vd$y)))
dirv <- cbind(cen$cx - ctr[1], cen$cy - ctr[2]); dirv <- dirv / pmax(sqrt(rowSums(dirv^2)), 1e-9)
# labels sit just outside the node cloud along the centroid's direction (leader line back to the centroid)
r_out <- stats::quantile(sqrt((vd$x - ctr[1])^2 + (vd$y - ctr[2])^2), 0.97) * opt$label_radius
cen$lx <- ctr[1] + dirv[, 1] * r_out; cen$ly <- ctr[2] + dirv[, 2] * r_out
cen$label <- vapply(paste0(cen$module_name, ":", cen$term_tc), function(s) paste(strwrap(s, opt$label_wrap), collapse = "\n"), character(1))
cen$module_name <- factor(cen$module_name, levels = mods); vd$module_name <- factor(vd$module_name, levels = mods)

# repel data: label rows + every node as an empty-label obstacle so labels are pushed off the points
rep_df <- rbind(data.frame(x = cen$cx, y = cen$cy, label = cen$label, module_name = as.character(cen$module_name),
                           nx = cen$lx - cen$cx, ny = cen$ly - cen$cy),
                data.frame(x = vd$x, y = vd$y, label = "", module_name = as.character(vd$module_name), nx = 0, ny = 0))
rep_df$module_name <- factor(rep_df$module_name, levels = mods)
p_net <- ggplot() +
  geom_segment(data = ed, aes(x, y, xend = xend, yend = yend), colour = "grey78", alpha = 0.35, linewidth = 0.12) +
  geom_point(data = vd, aes(x, y, colour = module_name), size = opt$node_size, stroke = 0) +
  geom_text_repel(data = rep_df, aes(x = x, y = y, label = label, colour = module_name, segment.colour = module_name),
                  nudge_x = rep_df$nx, nudge_y = rep_df$ny, family = opt$font, fontface = "bold",
                  size = opt$label_mm, lineheight = 0.9, min.segment.length = 0, segment.size = 0.45, box.padding = 0.3,
                  point.padding = 0.05, point.size = opt$node_size, force = 4, force_pull = 1.5, max.overlaps = Inf,
                  max.iter = 20000, max.time = 600, seed = opt$seed, show.legend = FALSE) +
  scale_colour_manual(values = pal, aesthetics = c("colour", "segment.colour"), guide = "none") +
  coord_equal(clip = "off") +
  scale_x_continuous(expand = expansion(mult = 0.20)) + scale_y_continuous(expand = expansion(mult = 0.10)) +
  theme_void(base_family = opt$font) + theme(plot.margin = margin(4, 2, 4, 4))

# ---- per-module GO bar grid (linked by the same palette) ----
# shared x axis as in the original. If one module dominates (max > 2x the next module's max), cap the shared
# axis at the next module's max (rounded up to even) and print the true -log10(P) on capped bars.
mod_max <- sort(tapply(go$neglog10p, go$module_name, max), decreasing = TRUE)
xmax <- if (identical(opt$x_cap, "none")) ceiling(mod_max[1] / 2) * 2 else if (identical(opt$x_cap, "auto")) {
  if (length(mod_max) > 1 && mod_max[1] > 2 * mod_max[2]) ceiling(mod_max[2] / 2) * 2 else ceiling(mod_max[1] / 2) * 2
} else as.numeric(opt$x_cap)
go$capped <- go$neglog10p > xmax
x_step <- if (xmax > 10) 4 else 2
nrow_b <- ceiling(n_mod / opt$ncol_bars)
bar_plot <- function(m, show_x) {
  d <- go[go$module_name == m, ]; d <- d[order(d$pvalue), ]
  tc <- if (any(d$capped)) opt$term_chars_capped else opt$term_chars   # leave room for the "»value" tag
  d$lab <- ifelse(nchar(d$bar_label) > tc, paste0(substr(d$bar_label, 1, tc - 1), "\u2026"), d$bar_label)
  d$y <- factor(seq_len(nrow(d)), levels = rev(seq_len(nrow(d)))); d$module_name <- m
  ggplot(d, aes(x = neglog10p, y = y)) +
    geom_col(fill = lighten(pal[[m]]), width = 0.72) +
    geom_text(aes(x = 0.05, label = lab), hjust = 0, size = opt$bar_text_mm, family = opt$font, colour = "black") +
    geom_text(data = d[d$capped, , drop = FALSE], aes(x = xmax, label = sprintf("\u00BB%.1f", neglog10p)),
              hjust = 1, size = opt$bar_text_mm, family = opt$font, colour = "black", fontface = "bold") +
    facet_wrap(~module_name) +
    scale_x_continuous(limits = c(0, xmax), breaks = seq(0, xmax, x_step), expand = expansion(mult = c(0, 0.02)), oob = scales::squish) +
    coord_cartesian(clip = "on") + labs(x = NULL, y = NULL) +
    theme_bw(base_size = 6, base_family = opt$font) +
    theme(strip.background = element_rect(fill = pal[[m]], colour = "black", linewidth = 0.3),
          strip.text = element_text(colour = ink_for(pal[[m]]), size = opt$strip_pt, margin = margin(1.4, 0, 1.4, 0)),
          panel.grid = element_blank(), panel.border = element_blank(),
          axis.line.x = element_line(colour = "grey55", linewidth = 0.25),
          axis.text.y = element_blank(), axis.ticks.y = element_blank(),
          axis.text.x = if (show_x) element_text(size = opt$tick_pt) else element_blank(),
          axis.ticks.x = element_line(linewidth = 0.2), axis.ticks.length.x = unit(if (show_x) 1 else 0.6, "pt"),
          plot.margin = margin(1.2, 2, 1.2, 2))
}
idx_last <- seq_len(n_mod) > (nrow_b - 1) * opt$ncol_bars - (nrow_b * opt$ncol_bars - n_mod)
bars <- lapply(seq_len(n_mod), function(i) bar_plot(mods[i], idx_last[i]))
if (length(bars) < nrow_b * opt$ncol_bars) bars <- c(bars, list(plot_spacer()))
x_title <- wrap_elements(full = grid::textGrob("-log10(P-value)", gp = grid::gpar(fontsize = opt$xtitle_pt, fontfamily = opt$font)))
p_bars <- wrap_elements(full = wrap_plots(bars, ncol = opt$ncol_bars, byrow = TRUE)) / x_title +
  plot_layout(heights = c(60, 1.2))

fig <- (p_net | p_bars) + plot_layout(widths = c(opt$net_width, opt$bars_width)) &
  theme(plot.background = element_rect(fill = "white", colour = NA))
w_in <- opt$width_px / opt$dpi; h_in <- opt$height_px / opt$dpi
out <- function(ext) file.path(opt$outdir, paste0(opt$stem, ".", ext))
ragg::agg_png(out("png"), width = opt$width_px, height = opt$height_px, res = opt$dpi, background = "white")
print(fig); invisible(dev.off())
grDevices::cairo_pdf(out("pdf"), width = w_in, height = h_in, family = opt$font); print(fig); invisible(dev.off())
svglite::svglite(out("svg"), width = w_in, height = h_in); print(fig); invisible(dev.off())
write.table(data.frame(module_name = mods, hex = unname(pal), bar_fill = vapply(pal, lighten, ""), strip_ink = ink_for(pal)),
            file.path(opt$outdir, "palette_used.tsv"), sep = "\t", quote = FALSE, row.names = FALSE)
writeLines(c(sprintf("x_axis_max\t%s", xmax), sprintf("capped_terms\t%d", sum(go$capped)),
             sprintf("capped_modules\t%s", paste(unique(go$module_name[go$capped]), collapse = ","))),
           file.path(opt$outdir, "plot_summary.tsv"))
write.table(vd, file.path(opt$outdir, "network_layout.tsv"), sep = "\t", quote = FALSE, row.names = FALSE)
cat("wrote", out("png"), out("pdf"), out("svg"), "\n")
