using Test
using JuliaSyntax
println("JULIA-TRIGGER-START")
@testset "JULIA-507 transpose assignment expression" begin
    @test JuliaSyntax.parsestmt(Expr, "x' = A * x") ==
        Expr(:(=), Expr(Symbol("'"), :x), Expr(:call, :*, :A, :x))
end
