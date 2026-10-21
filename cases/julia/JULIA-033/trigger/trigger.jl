println("JULIA-TRIGGER-START")
using Test
using JuliaSyntax

@testset "JULIA-033 incomplete expression tags" begin
    JuliaSyntax.enable_in_core!()
    try
        @test Base.incomplete_tag(Meta.parse("f(1, ", raise=false)) == :other
        @test Base.incomplete_tag(Meta.parse("[x ", raise=false)) == :other
        @test Base.incomplete_tag(Meta.parse("( ", raise=false)) == :other
    finally
        JuliaSyntax.enable_in_core!(false)
    end
end

println("JULIA-033 trigger completed")
