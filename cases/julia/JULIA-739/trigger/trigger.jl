using Test
using JuliaSyntax

println("JULIA-TRIGGER-START")
@testset "Expr incomplete classification" begin
    JuliaSyntax.enable_in_core!()
    try
        @test Meta.isexpr(Meta.parse("[x"), :incomplete)
        @test Base.incomplete_tag(Meta.parse("let", raise=false)) == :block
    finally
        JuliaSyntax.enable_in_core!(false)
    end
end
