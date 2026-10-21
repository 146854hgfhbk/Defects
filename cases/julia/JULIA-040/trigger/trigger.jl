println("JULIA-TRIGGER-START")
using Test
using JuliaSyntax

function parse_to_sexpr(code)
    stream = JuliaSyntax.ParseStream(code, version=v"1.6")
    JuliaSyntax.parse_toplevel(JuliaSyntax.ParseState(stream))
    JuliaSyntax.validate_tokens(stream)
    tree = JuliaSyntax.build_tree(JuliaSyntax.GreenNode, stream)
    source = JuliaSyntax.SourceFile(code)
    sprint(show, MIME("text/x.sexpression"), JuliaSyntax.SyntaxNode(source, tree, keep_parens=true))
end

@testset "JULIA-040 generator trailing-junk recovery" begin
    @test parse_to_sexpr("(x for x = xs a)") ==
          "(toplevel (parens (generator x (iteration (in x xs))) (error-t a)))"
    @test parse_to_sexpr("f(x for x = xs a)") ==
          "(toplevel (call f (generator x (iteration (in x xs))) (error-t a)))"
end

println("JULIA-040 trigger completed")
