# d4x helper: run the package's testthat suite and print one identity line per test.
# Used when D4X_R_TRIGGERS is set, so the verdict is judged by trigger-test identity
# and not by the suite exit code (unrelated baseline failures otherwise fail the fixed side).
# NOT_CRAN=true: the trigger tests were recorded by the dataset's own runner; skip_on_cran()
# would otherwise silently skip them. This is a documented deviation.
Sys.setenv(NOT_CRAN = "true")
lib <- normalizePath(".d4x-lib", mustWork = FALSE)
if (dir.exists(lib)) .libPaths(c(lib, .libPaths()))
pkg <- read.dcf("DESCRIPTION")[1, "Package"]
testthat::set_max_fails(Inf)
res <- testthat::test_dir("tests/testthat", package = pkg, load_package = "installed",
                          reporter = "silent", stop_on_failure = FALSE,
                          stop_on_warning = FALSE)
df <- as.data.frame(res)
ctx <- if ("context" %in% names(df)) as.character(df$context) else rep(NA_character_, nrow(df))
clean <- function(x) { x <- gsub("[\t\r\n]+", " ", as.character(x)); x[is.na(x)] <- ""; x }
for (i in seq_len(nrow(df))) {
  st <- if (isTRUE(df$error[i]) || df$failed[i] > 0) "fail"
        else if (isTRUE(df$skipped[i])) "skip" else "ok"
  cat(sprintf("D4X_TEST\t%s\t%s\t%s\t%s\n", clean(df$file[i]), clean(ctx[i]), clean(df$test[i]), st))
}
cat("D4X_COMPLETE\n")
