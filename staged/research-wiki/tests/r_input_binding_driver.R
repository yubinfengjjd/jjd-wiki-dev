args <- commandArgs(trailingOnly = TRUE)
source(args[1])
columns <- list(
  group = list(type = "str", description = "细胞类型"),
  feature = list(type = "str", description = "基因"),
  avg_expression = list(type = "float", description = "平均表达"),
  pct_expressed = list(type = "float", description = "阳性细胞百分比，0–100"),
  target_group = list(type = "str", description = "目标细胞类型", required = FALSE)
)
mapping <- c(group = "cell_type", feature = "gene_symbol", avg_expression = "mean_expr",
             pct_expressed = "positive_percent")
mode <- if (length(args) >= 4) args[4] else "full"
if (mode == "full") mapping <- c(mapping, target_group = "target_cell_type")
report <- prepare_binding_table(columns, "my_results.csv", args[2], args[3],
                                "render-dotplot-long", mapping)
expected <- c("group", "feature", "avg_expression", "pct_expressed")
if (mode == "full") expected <- c(expected, "target_group")
stopifnot(identical(report$included_columns, expected))
expected_extras <- if (mode == "full") "cluster" else c("target_cell_type", "cluster")
stopifnot(identical(report$extras_preserved, expected_extras))
if (mode == "optional") stopifnot(identical(report$omitted_optional, "target_group"))
cat("OK\n")
