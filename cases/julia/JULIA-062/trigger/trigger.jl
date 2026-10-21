using Test
using JuliaSyntax

function parse_to_sexpr(code)
    stream = JuliaSyntax.ParseStream(code, version=v"1.6")
    JuliaSyntax.parse_factor(JuliaSyntax.ParseState(stream))
    JuliaSyntax.validate_tokens(stream)
    tree = JuliaSyntax.build_tree(JuliaSyntax.GreenNode, stream)
    source = JuliaSyntax.SourceFile(code)
    node = JuliaSyntax.SyntaxNode(source, tree, keep_parens=true)
    return sprint(io -> show(io, MIME("text/x.sexpression"), node))
end

println("JULIA-TRIGGER-START")
@testset "interpolated arrow arguments" begin
    @test parse_to_sexpr(raw"$a->b") == raw"(-> (tuple ($ a)) b)"
    @test parse_to_sexpr(raw"$(a)->b") == raw"(-> (tuple ($ (parens a))) b)"
end
