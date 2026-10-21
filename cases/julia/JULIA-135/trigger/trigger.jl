using Test
import MathOptInterface

const MOI = MathOptInterface

println("JULIA-TRIGGER-START")

@testset "JULIA-135 rejects open SemiToBinary intervals" begin
    for set in Any[
        MOI.Semicontinuous(1.0, Inf),
        MOI.Semicontinuous(-1.0, Inf),
        MOI.Semicontinuous(-Inf, 1.0),
        MOI.Semicontinuous(-Inf, -1.0),
        MOI.Semiinteger(1.0, Inf),
        MOI.Semiinteger(-1.0, Inf),
        MOI.Semiinteger(-Inf, 1.0),
        MOI.Semiinteger(-Inf, -1.0),
    ]
        model = MOI.Utilities.Model{Float64}()
        bridged = MOI.Bridges.Constraint.SemiToBinary{Float64}(model)
        x = MOI.add_variable(bridged)
        @test_throws MOI.AddConstraintNotAllowed{MOI.VariableIndex,typeof(set)} MOI.add_constraint(bridged, x, set)

        model = MOI.Utilities.Model{Float64}()
        bridged = MOI.Bridges.Constraint.SemiToBinary{Float64}(model)
        x = MOI.add_variable(bridged)
        c = MOI.add_constraint(bridged, x, typeof(set)(1.0, 2.0))
        @test_throws MOI.SetAttributeNotAllowed MOI.set(bridged, MOI.ConstraintSet(), c, set)
    end
end
