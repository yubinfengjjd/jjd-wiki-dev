# Minimal --key value parser (no extra packages). defaults: named list.
parse_cli <- function(defaults, required = character()) {
  a <- commandArgs(trailingOnly = TRUE); out <- defaults
  i <- 1
  while (i <= length(a)) {
    k <- sub("^--", "", a[i]); if (!grepl("^--", a[i])) stop("bad arg: ", a[i])
    v <- if (i + 1 <= length(a)) a[i + 1] else stop("missing value for ", a[i])
    d <- defaults[[k]]
    out[[k]] <- if (length(d) == 1 && is.na(d)) v else if (is.numeric(d)) as.numeric(v) else if (is.logical(d)) as.logical(v) else v
    i <- i + 2
  }
  miss <- required[vapply(required, function(r) is.null(out[[r]]) || identical(out[[r]], NA), logical(1))]
  if (length(miss)) stop("missing required args: ", paste0("--", miss, collapse = ", "))
  out
}
