println("JULIA-TRIGGER-START")
using Test
using DiskArrays
using DiskArrays.TestTypes

@testset "JULIA-255 zero-length copyto!" begin
    source = AccessCountDiskArray(collect(reshape(1:90, 10, 9)); chunksize=(5, 3))
    empty_destination = Matrix{Int}(undef, 0, 2)
    copyto!(empty_destination, CartesianIndices((1:0, 1:2)), source,
            CartesianIndices((8:7, 8:9)))
    @test size(empty_destination) == (0, 2)

    destination = zeros(Int, 3, 2)
    @test_throws ArgumentError copyto!(destination,
        CartesianIndices((1:1, 1:2)), source, CartesianIndices((4:6, 8:9)))
end
println("JULIA-255 trigger completed")
