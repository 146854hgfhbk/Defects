println("JULIA-TRIGGER-START")
using Test
using JuliaSyntax

@testset "JULIA-027 standalone syntactic assignments" begin
    # The regression is the standalone assignment-precedence operator being
    # rejected as an identifier.  Use the same atom-level public API as the
    # upstream parser test; parseall wraps the result in a toplevel node.
    @test JuliaSyntax.parseatom(Expr, "≔"; ignore_errors=true) == Symbol("≔")
end
