using JuliaSyntax

# Reproducer from issue #8. With the Core parsing hook enabled, invalid syntax
# must preserve JuliaSyntax.ParseError instead of throwing an unrelated conversion error.
JuliaSyntax.enable_in_core!()
try
    caught = false
    try
        Meta.parse("[(1,2]")
    catch err
        caught = err isa JuliaSyntax.ParseError
    end
    @assert caught
finally
    JuliaSyntax.disable_in_core!()
end
