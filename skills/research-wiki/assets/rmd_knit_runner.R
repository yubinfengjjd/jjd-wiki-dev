# rwiki L1 runner: knit an upstream R Markdown module as-is.
# No pandoc, no network installs: install_dependencies.R has been replaced by a check stub.
args <- commandArgs(trailingOnly = TRUE)
rmd <- args[[1]]
out <- if (length(args) >= 2) args[[2]] else "rwiki-knit.md"
Sys.setenv(LANGUAGE = "en")
options(warn = 1, stringsAsFactors = FALSE,
        repos = c(CRAN = "http://127.0.0.1:9"), BioC_mirror = "http://127.0.0.1:9")
for (pkg in c("knitr", "rmarkdown", "jsonlite")) {
  if (!requireNamespace(pkg, quietly = TRUE)) stop("rwiki: runner needs package ", pkg, call. = FALSE)
}
front <- tryCatch(rmarkdown::yaml_front_matter(rmd), error = function(e) list())
# Knit in the global environment, as RStudio "Knit"/interactive runs do: survminer::ggsurvplot
# and rms::datadist look their data up in the global environment.
env <- globalenv()
if (!is.null(front$params)) assign("params", front$params, envir = env)
blocked <- function(...) stop("rwiki: package installation is blocked during runs", call. = FALSE)
assign("install.packages", blocked, envir = env)
knitr::opts_chunk$set(dev = "png", dpi = 96, fig.path = "rwiki-figure/", error = FALSE)
status <- tryCatch({
  knitr::knit(rmd, output = out, envir = env, quiet = TRUE)
  "ok"
}, error = function(e) {
  message("rwiki-error: ", conditionMessage(e))
  "error"
})
names <- sort(loadedNamespaces())
versions <- vapply(names, function(p) tryCatch(as.character(utils::packageVersion(p)),
                                               error = function(e) ""), "")
jsonlite::write_json(list(status = status, r_version = R.version.string, packages = as.list(versions)),
                     "rwiki-session.json", auto_unbox = TRUE, pretty = TRUE)
if (status != "ok") quit(save = "no", status = 1)
