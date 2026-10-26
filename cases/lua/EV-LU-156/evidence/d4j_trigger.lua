-- Curator trigger for the Windows/DOS fallback return contract, runnable on Linux.
-- It changes only the platform flag before loading pl.dir; production code itself is unmodified.
package.path = "./lua/?.lua;./lua/?/init.lua;" .. package.path
local path = require "pl.path"
path.is_windows = true
path.tmpname = function() return os.tmpname() end -- Linux harness adaptation; production pl.dir remains unmodified
package.loaded["pl.dir"] = nil
local dir = require "pl.dir"
local src = "__d4j_nonexistent_source__"
local dst = "__d4j_nonexistent_dest__"
local ok = dir.copyfile(src, dst)
assert(ok == false, "DOS fallback failure must return boolean false, got " .. tostring(ok))
print("PASS")
