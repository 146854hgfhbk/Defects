using Test
using SymbolicUtils

@testset "JULIA-422 preserves numeric types in metadata equality" begin
    @syms x
    tmp1 = x ^ 3.0
    tmp2 = x ^ 3
    @test !SymbolicUtils.isequal_with_metadata(tmp1, tmp2)
    @test arguments(tmp1)[2] isa Float64
    @test arguments(tmp2)[2] isa Int
    tmp1 = 2tmp1
    tmp2 = 2tmp2
    @test !SymbolicUtils.isequal_with_metadata(tmp1, tmp2)
    @test arguments(arguments(tmp1)[2])[2] isa Float64
    @test arguments(arguments(tmp2)[2])[2] isa Int
end

println("JULIA-422 trigger completed")
