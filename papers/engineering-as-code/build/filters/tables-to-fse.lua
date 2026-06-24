-- tables-to-fse.lua — Pandoc Lua filter for FSE LaTeX output.
-- Converts Pandoc Table elements to ACM-compatible table* environments with
-- booktabs-style horizontal rules and proportional p{width} columns.
--
-- Run after pandoc-crossref and citeproc so references are already resolved.

local ROW_SEP = ' \\\\\n'

local function cell_to_latex(cell)
  -- Table cells are Blocks; take the inlines of the first Plain/Para block.
  local inlines = {}
  if cell and cell.contents and #cell.contents > 0 then
    local first = cell.contents[1]
    if first.tag == 'Plain' or first.tag == 'Para' then
      inlines = first.content
    end
  end
  local latex = pandoc.write(pandoc.Pandoc({pandoc.Plain(inlines)}), 'latex')
  -- Trim surrounding whitespace/newlines and collapse internal newlines so
  -- each table cell stays on a single row.
  return latex:gsub('^%s+', ''):gsub('%s+$', ''):gsub('\n', ' ')
end

local function row_to_latex(row)
  local parts = {}
  for _, cell in ipairs(row.cells) do
    parts[#parts + 1] = cell_to_latex(cell)
  end
  return table.concat(parts, ' & ')
end

local function build_col_spec(ncols)
  if ncols == 0 then
    return ''
  end
  local slack = 0.12
  local usable = 1.0 - slack
  local widths = {}
  if ncols >= 3 then
    local first = math.min(0.16, usable / ncols)
    local rest = (usable - first) / (ncols - 1)
    widths[1] = first
    for i = 2, ncols do
      widths[i] = rest
    end
  else
    local w = usable / ncols
    for i = 1, ncols do
      widths[i] = w
    end
  end

  local parts = {'@{}'}
  for _, w in ipairs(widths) do
    parts[#parts + 1] =
      string.format('>{\\raggedright\\arraybackslash}p{%.3f\\textwidth}', w)
  end
  parts[#parts + 1] = '@{}'
  return table.concat(parts, ' ')
end

function Table(el)
  if FORMAT ~= 'latex' then
    return nil
  end

  local ncols = #el.colspecs
  if ncols == 0 then
    return nil
  end

  local caption = pandoc.utils.stringify(el.caption.long)
  local label = el.identifier or ''

  -- Header rows
  local header_lines = {}
  for _, row in ipairs(el.head.rows) do
    header_lines[#header_lines + 1] = row_to_latex(row)
  end

  -- Body rows
  local body_lines = {}
  for _, body in ipairs(el.bodies) do
    for _, row in ipairs(body.body) do
      body_lines[#body_lines + 1] = row_to_latex(row)
    end
  end

  if #body_lines == 0 then
    return nil
  end

  local col_spec = build_col_spec(ncols)

  local latex = '\\begin{table*}\n\\centering\n'
  if caption ~= '' then
    latex = latex .. '\\caption{' .. caption .. '}'
    if label ~= '' then
      latex = latex .. '\\label{' .. label .. '}'
    end
    latex = latex .. '\n'
  end
  latex = latex .. '\\begin{tabular}{' .. col_spec .. '}\n'
  latex = latex .. '\\toprule\n'
  if #header_lines > 0 then
    latex = latex .. table.concat(header_lines, ROW_SEP) .. ROW_SEP
    latex = latex .. '\\midrule\n'
  end
  latex = latex .. table.concat(body_lines, ROW_SEP) .. ROW_SEP
  latex = latex .. '\\bottomrule\n'
  latex = latex .. '\\end{tabular}\n\\end{table*}'

  return pandoc.RawBlock('latex', latex)
end
