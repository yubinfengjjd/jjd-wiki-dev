# Copyable, base-R table adapter for explicit external-data bindings.
# It mirrors rwiki/input_binding.py: map declared internal fields to author
# columns and optionally melt/pivot without aggregation. It never guesses
# columns, fills values, converts units, or reads a network path.

binding_error <- function(...) stop(sprintf(...), call. = FALSE)

.missing_tokens <- c("", "na", "n/a", "nan", "null")
.is_missing <- function(x) is.na(x) | tolower(trimws(as.character(x))) %in% .missing_tokens

.binding_semantics <- paste0(
  "只核对字段存在、必填关系与数值可解析；不验证单位、粒度、配对关系或统计含义；",
  "不做 0–1 / 0–100 换算。")

.fs_available <- function() {
  Sys.getenv("RWIKI_DISABLE_FS") != "1" && requireNamespace("fs", quietly = TRUE)
}

.same_file <- function(left, right) {
  if (identical(tolower(normalizePath(left, mustWork = FALSE)),
                tolower(normalizePath(right, mustWork = FALSE)))) return(TRUE)
  if (!file.exists(left) || !file.exists(right)) return(FALSE)
  # Base R has no inode/alias comparison. Use fs when present so hard links and
  # symlinks are rejected early; the write path below never overwrites an
  # existing directory entry, so an undetected alias still cannot change a source.
  if (.fs_available()) {
    a <- fs::file_info(left)
    b <- fs::file_info(right)
    return(identical(a$device_id, b$device_id) && identical(a$inode, b$inode))
  }
  FALSE
}

.read_binding_csv <- function(path) {
  if (!file.exists(path)) binding_error("绑定源文件不存在: %s", path)
  rows <- utils::read.table(path, sep = ",", header = TRUE, check.names = FALSE,
                            colClasses = "character", quote = "\"", comment.char = "",
                            na.strings = character(), stringsAsFactors = FALSE)
  header <- names(rows)
  if (!length(header)) binding_error("CSV 没有表头")
  if (any(!nzchar(trimws(header)))) binding_error("CSV 存在空列名")
  duplicated_names <- unique(header[duplicated(header)])
  if (length(duplicated_names)) {
    binding_error("CSV 重复列名: %s", paste(duplicated_names, collapse = ", "))
  }
  list(header = header, rows = rows)
}

.check_columns <- function(value, name, header, allow_empty = FALSE) {
  if (is.null(value)) value <- character()
  if (!is.character(value) || any(!nzchar(value))) binding_error("reshape.%s 必须为字符串列表", name)
  if (!length(value) && !allow_empty) binding_error("reshape.%s 不得为空", name)
  missing <- setdiff(value, header)
  if (length(missing)) binding_error("reshape.%s 引用不存在的列: %s", name, paste(missing, collapse = ", "))
  if (anyDuplicated(value)) binding_error("reshape.%s 不得重复", name)
  value
}

.reshape_binding <- function(header, rows, reshape = NULL) {
  if (is.null(reshape)) return(list(header = header, rows = rows, operation = NULL))
  op <- reshape$op
  if (!op %in% c("melt", "pivot")) binding_error("reshape.op 必须为 melt 或 pivot")
  carry <- .check_columns(reshape$carry, "carry", header, allow_empty = TRUE)
  if (op == "melt") {
    allowed <- c("op", "id", "variables", "variable_name", "value_name", "carry")
    unknown <- setdiff(names(reshape), allowed)
    if (length(unknown)) binding_error("reshape 不支持字段: %s", paste(unknown, collapse = ", "))
    ids <- .check_columns(reshape$id, "id", header, allow_empty = TRUE)
    variables <- .check_columns(reshape$variables, "variables", header)
    variable_name <- reshape$variable_name
    value_name <- reshape$value_name
    if (!is.character(variable_name) || !is.character(value_name) ||
        !nzchar(variable_name) || !nzchar(value_name) || identical(variable_name, value_name)) {
      binding_error("reshape.variable_name/value_name 必须为不同的非空字符串")
    }
    if (length(intersect(ids, variables)) || length(intersect(carry, union(ids, variables)))) {
      binding_error("reshape 的 id/variables/carry 列不得重叠")
    }
    out_header <- c(ids, variable_name, value_name, carry)
    if (anyDuplicated(out_header)) binding_error("reshape 输出列名重复")
    pieces <- list()
    for (i in seq_len(nrow(rows))) {
      for (variable in variables) {
        item <- rows[i, ids, drop = FALSE]
        item[[variable_name]] <- variable
        item[[value_name]] <- rows[[variable]][i]
        for (name in carry) item[[name]] <- rows[[name]][i]
        pieces[[length(pieces) + 1]] <- item
      }
    }
    out <- do.call(rbind, pieces)
    return(list(header = out_header, rows = out[, out_header, drop = FALSE],
                operation = list(op = "melt", id = ids, variables = variables,
                                 variable_name = variable_name, value_name = value_name,
                                 carry = carry, aggregation = FALSE,
                                 dropped_columns = setdiff(header, c(ids, variables, carry)))))
  }
  allowed <- c("op", "index", "columns", "values", "carry")
  unknown <- setdiff(names(reshape), allowed)
  if (length(unknown)) binding_error("reshape 不支持字段: %s", paste(unknown, collapse = ", "))
  index <- .check_columns(reshape$index, "index", header)
  columns <- reshape$columns
  values <- reshape$values
  if (!is.character(columns) || !is.character(values) || !nzchar(columns) || !nzchar(values)) {
    binding_error("reshape.columns/values 必须为非空字符串")
  }
  if (columns %in% index || values %in% index || identical(columns, values)) {
    binding_error("reshape 的 index/columns/values 列不得重叠")
  }
  if (!columns %in% header || !values %in% header) binding_error("reshape.columns/values 引用不存在的列")
  if (length(intersect(carry, c(index, columns, values)))) {
    binding_error("reshape 的 index/columns/values/carry 列不得重叠")
  }
  pivot_raw <- rows[[columns]]
  if (any(is.na(pivot_raw)) || any(!nzchar(as.character(pivot_raw)))) {
    binding_error("reshape pivot 列含空值/缺失值，无法确定稳定列名；请先明确处理")
  }
  # Identify index tuples by value identity, never by a separator-joined string.
  keys <- list()
  key_ids <- integer(nrow(rows))
  for (i in seq_len(nrow(rows))) {
    key <- if (length(index)) as.list(rows[i, index, drop = FALSE]) else list()
    id <- which(vapply(keys, function(item) identical(item, key), logical(1)))
    if (!length(id)) {
      keys[[length(keys) + 1]] <- key
      id <- length(keys)
    }
    key_ids[i] <- id
  }
  pivot_values <- unique(pivot_raw)
  value_matrix <- matrix("", nrow = length(keys), ncol = length(pivot_values))
  present <- matrix(FALSE, nrow = length(keys), ncol = length(pivot_values))
  carried <- vector("list", length(keys))
  for (i in seq_len(nrow(rows))) {
    key_id <- key_ids[i]
    pivot_id <- match(pivot_raw[i], pivot_values)
    if (present[key_id, pivot_id]) {
      label <- if (length(keys[[key_id]])) paste(unlist(keys[[key_id]]), collapse = " / ") else ""
      binding_error("reshape pivot 重复键: %s / %s", label, pivot_raw[i])
    }
    present[key_id, pivot_id] <- TRUE
    value_matrix[key_id, pivot_id] <- rows[[values]][i]
    for (name in carry) {
      if (!is.null(carried[[key_id]][[name]]) && !identical(carried[[key_id]][[name]], rows[[name]][i])) {
        binding_error("reshape carry 列 %s 在同一 index 下不唯一", name)
      }
      carried[[key_id]][[name]] <- rows[[name]][i]
    }
  }
  out_header <- c(index, pivot_values, carry)
  if (anyDuplicated(out_header)) binding_error("reshape 输出列名重复")
  out <- list()
  for (id in seq_along(keys)) {
    item <- keys[[id]]
    for (j in seq_along(pivot_values)) {
      item[[as.character(pivot_values[j])]] <- if (present[id, j]) value_matrix[id, j] else ""
    }
    for (name in carry) item[[name]] <- carried[[id]][[name]]
    out[[length(out) + 1]] <- as.data.frame(item, stringsAsFactors = FALSE)
  }
  if (!length(out)) {
    empty <- setNames(replicate(length(out_header), character(0), simplify = FALSE), out_header)
    out <- as.data.frame(empty, stringsAsFactors = FALSE)
  } else {
    out <- do.call(rbind, out)
  }
  list(header = out_header, rows = out[, out_header, drop = FALSE],
       operation = list(op = "pivot", index = index, columns = columns, values = values,
                        carry = carry, aggregation = FALSE,
                        missing_cells = sum(!present),
                        dropped_columns = setdiff(header, c(index, columns, values, carry))))
}

.map_binding <- function(header, rows, columns, mapping = list()) {
  if (is.null(mapping)) mapping <- list()
  if (is.character(mapping)) mapping <- as.list(mapping)
  if (!is.list(mapping) || (length(mapping) && (is.null(names(mapping)) || any(!nzchar(unlist(mapping)))))) {
    binding_error("bindings columns 必须为“内部字段 → 作者列”的字符串映射")
  }
  unknown <- setdiff(names(mapping), names(columns))
  if (length(unknown)) binding_error("bindings 映射含未知字段: %s", paste(unknown, collapse = ", "))
  external_values <- unlist(mapping, use.names = FALSE)
  if (anyDuplicated(external_values)) {
    binding_error("bindings 映射重复: %s", paste(unique(external_values[duplicated(external_values)]), collapse = ", "))
  }
  for (internal in names(mapping)) {
    if (!mapping[[internal]] %in% header) {
      binding_error("映射的外部列不存在: %s → %s", internal, mapping[[internal]])
    }
  }
  included <- character()
  missing <- character()
  for (internal in names(columns)) {
    external <- if (internal %in% names(mapping)) mapping[[internal]] else internal
    required <- isTRUE(columns[[internal]]$required %||% TRUE)
    if (external %in% header) included <- c(included, internal)
    else if (required) missing <- c(missing, internal)
  }
  if (length(missing)) binding_error("缺少必需字段: %s", paste(missing, collapse = ", "))
  effective <- vapply(included, function(name) {
    if (name %in% names(mapping)) mapping[[name]] else name
  }, character(1), USE.NAMES = FALSE)
  names(effective) <- included
  by_source <- split(included, effective)
  conflicts <- names(by_source)[lengths(by_source) > 1]
  if (length(conflicts)) {
    binding_error("同一来源列被多个内部字段消费: %s → %s",
                  conflicts[1], paste(by_source[[conflicts[1]]], collapse = ", "))
  }
  consumed <- unique(unname(effective))
  extras <- setdiff(header, consumed)
  if (length(intersect(extras, included))) binding_error("输出列名冲突: %s", paste(intersect(extras, included), collapse = ", "))
  out_header <- c(included, extras)
  out <- rows[, effective, drop = FALSE]
  names(out) <- included
  if (length(extras)) out <- cbind(out, rows[, extras, drop = FALSE])
  list(header = out_header, rows = out[, out_header, drop = FALSE],
       report = list(mapping = mapping, included_columns = included,
                     omitted_optional = setdiff(names(columns), included),
                     extras_preserved = extras))
}

`%||%` <- function(a, b) if (is.null(a)) b else a

.numeric_checks <- function(header, rows, columns, mapping = list()) {
  missing <- list(); ranges <- list(); warnings <- character()
  for (name in names(columns)) {
    if (!name %in% header || !columns[[name]]$type %in% c("float", "int")) next
    raw <- rows[[name]]
    present <- !.is_missing(raw)
    values <- suppressWarnings(as.numeric(raw[present]))
    if (any(is.na(values))) {
      bad <- raw[present][is.na(values)][1]
      external <- if (name %in% names(mapping)) mapping[[name]] else name
      binding_error("列 %s（%s）不是有效数值: %s", name, external, bad)
    }
    if (any(!is.finite(values))) {
      external <- if (name %in% names(mapping)) mapping[[name]] else name
      binding_error("列 %s（%s）不是有限数值", name, external)
    }
    count <- sum(!present)
    if (count) missing[[name]] <- count
    if (length(values)) {
      ranges[[name]] <- c(min(values), max(values))
      description <- columns[[name]]$description %||% ""
      external <- if (name %in% names(mapping)) mapping[[name]] else name
      if (grepl("0[[:space:]]*[–-][[:space:]]*100", description) && min(values) >= 0 && max(values) <= 1) {
        warnings <- c(warnings, sprintf("%s 声明为 0–100 百分比，但观测值均在 0–1；请确认是否为比例，本工具不自动换算", external))
      } else if (grepl("0[[:space:]]*[–-][[:space:]]*1([^0-9]|$)", description) && max(values) > 1) {
        warnings <- c(warnings, sprintf("%s 声明为 0–1，但观测值超过 1；请确认单位，本工具不自动换算", external))
      }
    }
  }
  list(missing_values = missing, observed_ranges = ranges, warnings = warnings)
}

#' Explicit, non-aggregating melt/pivot on an in-memory data.frame.
reshape_table <- function(df, reshape = NULL) {
  header <- names(df)
  rows <- as.data.frame(lapply(df, as.character), stringsAsFactors = FALSE, check.names = FALSE)
  names(rows) <- header
  .reshape_binding(header, rows, reshape)$rows
}

#' Bind an in-memory data.frame without any file or Wiki access.
bind_table <- function(df, columns, mapping = list()) {
  header <- names(df)
  rows <- as.data.frame(lapply(df, as.character), stringsAsFactors = FALSE, check.names = FALSE)
  names(rows) <- header
  mapped <- .map_binding(header, rows, columns, mapping)
  numeric <- .numeric_checks(mapped$header, mapped$rows, columns, mapping)
  c(mapped, list(numeric = numeric, semantics = .binding_semantics))
}

#' Read an explicit file, then bind it; no network, no implicit directory scan.
prepare_binding_table <- function(columns, file, data_root, work_dir, interface,
                                  mapping = list(), reshape = NULL, other_sources = character()) {
  if (!is.character(file) || !nzchar(file) || grepl("://", file)) {
    binding_error("bindings.file 必须为本地相对路径")
  }
  if (grepl("^([A-Za-z]:|/|\\\\)", file) || grepl("(^|[/\\\\])\\.\\.?([/\\\\]|$)", file)) {
    binding_error("bindings 路径越界: %s", file)
  }
  root <- normalizePath(data_root, mustWork = TRUE)
  source <- normalizePath(file.path(root, file), mustWork = FALSE)
  # normalizePath() uses backslashes on Windows while .Platform$file.sep is "/".
  # A component boundary must accept both separators and reject sibling prefixes.
  inside <- !identical(tolower(source), tolower(root)) &&
    (startsWith(tolower(source), tolower(paste0(root, "/"))) ||
     startsWith(tolower(source), tolower(paste0(root, "\\"))))
  if (!inside || !file.exists(source)) binding_error("bindings 源文件不存在或越界: %s", file)
  dir.create(work_dir, recursive = TRUE, showWarnings = FALSE)
  out_path <- file.path(work_dir, paste0(interface, ".csv"))
  if (file.exists(out_path) && isTRUE(file.info(out_path)$isdir)) {
    binding_error("输出路径是目录: %s", out_path)
  }
  out_norm <- normalizePath(out_path, mustWork = FALSE)
  reserved <- c(source, other_sources)
  reserved <- reserved[file.exists(reserved)]
  if (tolower(out_norm) %in% tolower(normalizePath(reserved, mustWork = TRUE))) {
    binding_error("输出文件会覆盖源文件: %s", out_path)
  }
  if (length(reserved) && any(vapply(reserved, function(item) .same_file(out_path, item), logical(1)))) {
    binding_error("输出文件会覆盖源文件: %s", out_path)
  }
  read <- .read_binding_csv(source)
  reshaped <- .reshape_binding(read$header, read$rows, reshape)
  mapped <- .map_binding(reshaped$header, reshaped$rows, columns, mapping)
  numeric <- .numeric_checks(mapped$header, mapped$rows, columns, mapping)
  sha <- if (requireNamespace("openssl", quietly = TRUE)) as.character(openssl::sha256(file(source))) else NA_character_
  staged <- tempfile(pattern = paste0(".", interface, "-"), tmpdir = work_dir, fileext = ".csv")
  on.exit(unlink(staged), add = TRUE)
  utils::write.csv(mapped$rows, staged, row.names = FALSE, na = "")
  # Never write through an existing directory entry: an output may be a hard
  # link/symlink to a source, which file.copy(overwrite=TRUE) would modify.
  # Move the old entry aside, rename the staged file into place, then drop the
  # backup. On failure, restore the old entry.
  backup <- NULL
  if (file.exists(out_path)) {
    backup <- tempfile(pattern = paste0(".", interface, "-backup-"), tmpdir = work_dir, fileext = ".csv")
    if (!file.rename(out_path, backup)) binding_error("无法移开已有输出: %s", out_path)
  }
  if (!file.rename(staged, out_path)) {
    if (!is.null(backup) && file.exists(backup)) file.rename(backup, out_path)
    binding_error("无法写入规范表: %s", out_path)
  }
  if (!is.null(backup)) unlink(backup)
  out_sha <- if (requireNamespace("openssl", quietly = TRUE)) as.character(openssl::sha256(file(out_path))) else NA_character_
  list(table_key = NULL, interface = interface, source_file = file,
       source_sha256 = sha, output_file = basename(out_path), output_sha256 = out_sha,
       mapping = mapping, included_columns = mapped$report$included_columns,
       omitted_optional = mapped$report$omitted_optional,
       extras_preserved = mapped$report$extras_preserved,
       reshape = reshaped$operation, checks = c("source_inside_data_root", "header_unique",
                                                "required_columns_present", "numeric_values_parse"),
       semantics = .binding_semantics, missing_values = numeric$missing_values,
       observed_ranges = numeric$observed_ranges, warnings = numeric$warnings)
}
