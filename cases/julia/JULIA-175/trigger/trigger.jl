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
@testset "typed unary expression parsing" begin
    @test parse_to_sexpr("-1::T") == "(toplevel (::-i -1 T))"
end
