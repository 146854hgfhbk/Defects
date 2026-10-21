using Test
import MathOptInterface as MOI

struct EmptyObjectiveModel <: MOI.ModelLike end
MOI.get(::EmptyObjectiveModel, ::MOI.ObjectiveFunctionType) = nothing
MOI.get(::EmptyObjectiveModel, ::MOI.ListOfConstraintTypesPresent) = Tuple{Type,Type}[]

println("JULIA-TRIGGER-START")
@testset "active bridges handles absent objective" begin
    model = MOI.Bridges.full_bridge_optimizer(EmptyObjectiveModel(), Float64)
    @test MOI.get(model, MOI.ObjectiveFunctionType()) === nothing
    @test sprint(MOI.Bridges.print_active_bridges, model) == ""
end
