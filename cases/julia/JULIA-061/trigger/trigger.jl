using Test
using JuliaSyntax

function parse_to_sexpr(code)
    stream = JuliaSyntax.ParseStream(code, version=v"1.6")
    JuliaSyntax.parse_toplevel(JuliaSyntax.ParseState(stream))
    JuliaSyntax.validate_tokens(stream)
    node = JuliaSyntax.build_tree(JuliaSyntax.SyntaxNode, stream, keep_parens=true)
    return sprint(io -> show(io, MIME("text/x.sexpression"), node))
end

println("JULIA-TRIGGER-START")
@testset "multiline function signatures" begin
    @test parse_to_sexpr("function (\n        ::T\n        )() end") ==
        "(toplevel (function (call (parens (::-pre T))) (block)))"
end
