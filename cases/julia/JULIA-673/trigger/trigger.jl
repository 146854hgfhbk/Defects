using Test
using GenericLinearAlgebra
using LinearAlgebra

println("JULIA-TRIGGER-START")
@testset "Empty matrices. Issue 70" begin
    @test svdvals!(Float16.(ones(10, 0))) == Float16[]
    @test svdvals!(Float16.(ones(0, 10))) == Float16[]
    U, s, Vt = svd!(Float16.(ones(10, 0)))
    @test U == Matrix{Float16}(undef, 10, 0)
    @test s == Float16[]
    @test Vt == Matrix{Float16}(undef, 0, 0)
    U, s, Vt = svd!(Float16.(ones(0, 10)))
    @test U == Matrix{Float16}(undef, 0, 0)
    @test s == Float16[]
    @test Vt == Matrix{Float16}(undef, 10, 0)
end
