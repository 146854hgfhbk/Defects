os = nil
io = nil
local ok, M = pcall(require, "moses")
assert(ok, "moses must load without io/os: "..tostring(M))
assert(type(M) == "table", "moses module expected")
print("PASS")
