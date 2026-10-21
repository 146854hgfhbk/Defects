println("JULIA-TRIGGER-START")
using Test
using DiskArrays
using DiskArrays.TestTypes

@testset "JULIA-242 CartesianIndex disk write" begin
    array = AccessCountDiskArray(reshape(collect(1:20), 4, 5, 1); chunksize=(2, 2, 1))
    array[CartesianIndex(1, 1, 1)] = -10
    @test trueparent(array)[1, 1, 1] == -10
end
println("JULIA-242 trigger completed")
