args <- commandArgs(trailingOnly = TRUE)
source(args[1])
mode <- args[2]
work <- args[3]
dir.create(work, recursive = TRUE, showWarnings = FALSE)

expect_error <- function(expr, pattern) {
  message <- tryCatch({ force(expr); NULL }, error = function(error) conditionMessage(error))
  if (is.null(message)) stop("expected error containing: ", pattern)
  if (!grepl(pattern, message, fixed = TRUE)) stop("unexpected error: ", message)
  invisible(message)
}

columns <- list(value = list(type = "int", description = "count"))

if (mode == "overwrite") {
  root <- file.path(work, "overwrite")
  dir.create(root, recursive = TRUE, showWarnings = FALSE)
  source_file <- file.path(root, "values.csv")
  writeLines(c("n", "2"), source_file)
  before <- readBin(source_file, "raw", file.info(source_file)$size)
  expect_error(prepare_binding_table(columns, "values.csv", root, root, "values",
                                     c(value = "n")), "覆盖源文件")
  after <- readBin(source_file, "raw", file.info(source_file)$size)
  stopifnot(identical(before, after))
  # Another table's source passed by a batch caller must also be protected.
  other_dir <- file.path(work, "other")
  dir.create(other_dir, recursive = TRUE, showWarnings = FALSE)
  other <- file.path(other_dir, "other-out.csv")
  writeLines(c("n", "3"), other)
  expect_error(prepare_binding_table(columns, "values.csv", root, other_dir, "other-out",
                                     c(value = "n"), other_sources = other), "覆盖源文件")
  # A filesystem alias of the source must not be replaced either.
  alias <- file.path(root, "alias.csv")
  if (isTRUE(file.link(source_file, alias))) {
    expect_error(prepare_binding_table(columns, "values.csv", root, root, "alias",
                                       c(value = "n")), "覆盖源文件")
  }
  cat("OK overwrite\n")
}

if (mode == "effective") {
  df <- data.frame(feature = "CD3", stringsAsFactors = FALSE)
  cols <- list(group = list(type = "str", description = "group"),
               feature = list(type = "str", description = "feature"))
  expect_error(bind_table(df, cols, c(group = "feature")), "同一来源列")
  cat("OK effective\n")
}

if (mode == "pivot") {
  df <- data.frame(a = c("x\ry", "", "dup"), b = c("z", "q", "dup"),
                   group = "g1", value = c("1", "2", "3"), stringsAsFactors = FALSE)
  shape <- list(op = "pivot", index = c("a", "b"), columns = "group", values = "value")
  out <- reshape_table(df, shape)
  stopifnot(identical(as.character(out$a[1]), "x\ry"))
  stopifnot(identical(as.character(out$a[2]), ""))
  utils::write.csv(out, file.path(work, "pivot.csv"), row.names = FALSE, na = "")
  expect_error(reshape_table(rbind(df, df[1, ]), shape), "重复键")
  empty <- data.frame(a = "x", b = "z", group = "", value = "1", stringsAsFactors = FALSE)
  expect_error(reshape_table(empty, shape), "空值")
  missing <- data.frame(a = NA_character_, b = "m", group = "g1", value = "3",
                        stringsAsFactors = FALSE)
  missing_out <- reshape_table(missing, shape)
  stopifnot(is.na(missing_out$a[[1]]))
  cat("OK pivot\n")
}

if (mode == "nofs-hardlink") {
  root <- file.path(work, "root")
  out <- file.path(work, "out")
  dir.create(root, recursive = TRUE, showWarnings = FALSE)
  dir.create(out, recursive = TRUE, showWarnings = FALSE)
  source_file <- file.path(root, "source.csv")
  if (!file.exists(source_file)) writeLines(c("n", "2"), source_file)
  alias <- file.path(out, "values.csv")
  if (!file.exists(alias)) {
    if (!isTRUE(file.link(source_file, alias))) stop("hardlink not available")
  }
  before <- readBin(source_file, "raw", file.info(source_file)$size)
  first <- prepare_binding_table(columns, "source.csv", root, out, "values", c(value = "n"))
  stopifnot(is.character(first$semantics), nzchar(first$semantics))
  stopifnot(identical(before, readBin(source_file, "raw", file.info(source_file)$size)))
  # A legal repeat over the now-independent output must also succeed safely.
  second <- prepare_binding_table(columns, "source.csv", root, out, "values", c(value = "n"))
  stopifnot(is.character(second$semantics), nzchar(second$semantics))
  stopifnot(identical(before, readBin(source_file, "raw", file.info(source_file)$size)))
  stopifnot(file.exists(alias))
  stopifnot(length(list.files(out, pattern = "backup")) == 0)
  cat("OK nofs-hardlink\n")
}

if (mode == "boundary") {
  root <- file.path(work, "data")
  sibling <- file.path(work, "data2")
  dir.create(root, recursive = TRUE, showWarnings = FALSE)
  dir.create(sibling, recursive = TRUE, showWarnings = FALSE)
  writeLines(c("n", "2"), file.path(sibling, "x.csv"))
  expect_error(prepare_binding_table(columns, "../data2/x.csv", root, work, "values",
                                     c(value = "n")), "越界")
  writeLines(c("n", "2"), file.path(root, "in.csv"))
  prepare_binding_table(columns, "in.csv", root, work, "values2", c(value = "n"))
  stopifnot(file.exists(file.path(work, "values2.csv")))
  cat("OK boundary\n")
}
