import numpy as np
import opti
import pandas as pd
from scipy.optimize import LinearConstraint, NonlinearConstraint

from doe.utils import (
    constraints_as_scipy_constraints,
    get_formula_from_string,
    get_jacobian_NChooseK,
    n_zero_eigvals,
)


def test_get_formula_from_string():
    problem = opti.Problem(
        inputs=[opti.Continuous(f"x{i}", [0, 1]) for i in range(3)],
        outputs=[opti.Continuous("y")],
    )

    # linear model
    terms = ["1", "x0", "x1", "x2"]
    model_formula = get_formula_from_string(problem=problem, model_type="linear")
    assert all(term in terms for term in model_formula.terms)
    assert all(term in model_formula.terms for term in terms)

    # linear and interaction
    terms = ["1", "x0", "x1", "x2", "x0:x1", "x0:x2", "x1:x2"]
    model_formula = get_formula_from_string(
        problem=problem, model_type="linear-and-interactions"
    )
    assert all(term in terms for term in model_formula.terms)
    assert all(term in model_formula.terms for term in terms)

    # linear and quadratic
    terms = ["1", "x0", "x1", "x2", "x0**2", "x1**2", "x2**2"]
    model_formula = get_formula_from_string(
        problem=problem, model_type="linear-and-quadratic"
    )
    assert all(term in terms for term in model_formula.terms)
    assert all(term in model_formula.terms for term in terms)

    # fully quadratic
    terms = [
        "1",
        "x0",
        "x1",
        "x2",
        "x0:x1",
        "x0:x2",
        "x1:x2",
        "x0**2",
        "x1**2",
        "x2**2",
    ]
    model_formula = get_formula_from_string(
        problem=problem, model_type="fully-quadratic"
    )
    assert all(term in terms for term in model_formula.terms)
    assert all(term in model_formula.terms for term in terms)

    # custom model
    terms_lhs = ["y"]
    terms_rhs = ["1", "x0", "x0**2", "x0:x1"]
    model_formula = get_formula_from_string(
        problem=problem, model_type="y ~ 1 + x0 + x0:x1 + {x0**2}", rhs_only=False
    )
    assert all(term in terms_lhs for term in model_formula.terms.lhs)
    assert all(term in model_formula.terms.lhs for term in terms_lhs)
    assert all(term in terms_rhs for term in model_formula.terms.rhs)
    assert all(term in model_formula.terms.rhs for term in terms_rhs)


def test_n_zero_eigvals_unconstrained():
    # 5 continous & 1 categorical inputs
    problem = opti.Problem(
        inputs=[opti.Continuous(f"x{i}", [0, 100]) for i in range(5)],
        outputs=[opti.Continuous("y")],
    )

    assert n_zero_eigvals(problem, "linear") == 0
    assert n_zero_eigvals(problem, "linear-and-quadratic") == 0
    assert n_zero_eigvals(problem, "linear-and-interactions") == 0
    assert n_zero_eigvals(problem, "fully-quadratic") == 0


def test_n_zero_eigvals_constrained():
    # 3 continuous & 2 discrete inputs, 1 mixture constraint
    prob = opti.Problem(
        inputs=[
            opti.Continuous("x1", domain=[0, 100]),
            opti.Continuous("x2", domain=[0, 100]),
            opti.Continuous("x3", domain=[0, 100]),
            opti.Discrete("discrete1", [0, 1, 5]),
            opti.Discrete("discrete2", [0, 1]),
        ],
        outputs=[opti.Continuous("y")],
        constraints=[opti.LinearEquality(["x1", "x2", "x3"], rhs=1)],
    )

    assert n_zero_eigvals(prob, "linear") == 1
    assert n_zero_eigvals(prob, "linear-and-quadratic") == 1
    assert n_zero_eigvals(prob, "linear-and-interactions") == 3
    assert n_zero_eigvals(prob, "fully-quadratic") == 6

    # TODO: NChooseK?


def test_number_of_model_terms():
    # 5 continous inputs
    problem = opti.Problem(
        inputs=[opti.Continuous(f"x{i}") for i in range(5)],
        outputs=[opti.Continuous("y")],
    )

    assert len(get_formula_from_string(problem=problem, model_type="linear").terms) == 6
    assert (
        len(
            get_formula_from_string(
                problem=problem, model_type="linear-and-quadratic"
            ).terms
        )
        == 11
    )
    assert (
        len(
            get_formula_from_string(
                problem=problem, model_type="linear-and-interactions"
            ).terms
        )
        == 16
    )
    assert (
        len(
            get_formula_from_string(problem=problem, model_type="fully-quadratic").terms
        )
        == 21
    )

    # 3 continuous & 2 discrete inputs
    problem = opti.Problem(
        inputs=[
            opti.Continuous("x1", domain=[0, 100]),
            opti.Continuous("x2", domain=[0, 100]),
            opti.Continuous("x3", domain=[0, 100]),
            opti.Discrete("discrete1", [0, 1, 5]),
            opti.Discrete("discrete2", [0, 1]),
        ],
        outputs=[opti.Continuous("y")],
    )

    assert len(get_formula_from_string(problem=problem, model_type="linear").terms) == 6
    assert (
        len(
            get_formula_from_string(
                problem=problem, model_type="linear-and-quadratic"
            ).terms
        )
        == 11
    )
    assert (
        len(
            get_formula_from_string(
                problem=problem, model_type="linear-and-interactions"
            ).terms
        )
        == 16
    )
    assert (
        len(
            get_formula_from_string(problem=problem, model_type="fully-quadratic").terms
        )
        == 21
    )


def test_constraints_as_scipy_constraints():
    # test problems from the paper "The construction of D- and I-optimal designs for
    # mixture experiments with linear constraints on the components" by R. Coetzer and
    # L. M. Haines.

    problem = opti.Problem(
        inputs=opti.Parameters([opti.Continuous(f"x{i+1}", [0, 1]) for i in range(3)]),
        outputs=[opti.Continuous("y")],
        constraints=[
            opti.LinearEquality(names=["x1", "x2", "x3"], rhs=1),
            opti.LinearInequality(["x2"], lhs=[-1], rhs=-0.1),
            opti.LinearInequality(["x3"], lhs=[1], rhs=0.6),
            opti.LinearInequality(["x1", "x2"], lhs=[5, 4], rhs=3.9),
            opti.LinearInequality(["x1", "x2"], lhs=[-20, 5], rhs=-3),
        ],
    )

    n_experiments = 2

    constraints = constraints_as_scipy_constraints(problem, n_experiments)

    for c in constraints:
        assert isinstance(c, LinearConstraint)
        assert c.A.shape == (n_experiments, problem.n_inputs * n_experiments)
        assert len(c.lb) == n_experiments
        assert len(c.ub) == n_experiments

    A = np.array([[1, 1, 1, 0, 0, 0], [0, 0, 0, 1, 1, 1]])
    lb = np.array([0.999, 0.999])
    ub = np.array([1.001, 1.001])
    assert np.allclose(constraints[0].A, A)
    assert np.allclose(constraints[0].lb, lb)
    assert np.allclose(constraints[0].ub, ub)

    lb = -np.inf * np.ones(n_experiments)
    ub = -0.1 * np.ones(n_experiments)
    assert np.allclose(constraints[1].lb, lb)
    assert np.allclose(constraints[1].ub, ub)

    # problem with nonlinear constraints
    problem = opti.Problem(
        inputs=opti.Parameters([opti.Continuous(f"x{i+1}", [0, 1]) for i in range(3)]),
        outputs=[opti.Continuous("y")],
        constraints=[
            opti.NonlinearEquality("x1**2 + x2**2 - 1"),
            opti.NonlinearInequality("x1**2 + x2**2 - 1"),
        ],
    )

    constraints = constraints_as_scipy_constraints(problem, n_experiments)

    for c in constraints:
        assert isinstance(c, NonlinearConstraint)
        assert len(c.lb) == n_experiments
        assert len(c.ub) == n_experiments
        assert np.allclose(c.fun(np.array([1, 1, 1, 1, 1, 1])), [1, 1])

    # problem with NChooseK constraint
    inputs = opti.Parameters([opti.Continuous(f"x{i}", [0, 1]) for i in range(4)])
    problem = opti.Problem(
        inputs=inputs,
        outputs=[opti.Continuous("y")],
        constraints=[opti.NChooseK(inputs.names, max_active=2)],
    )
    n_experiments = 5

    x = np.array(
        [
            [1, -10, 2, -1.5],
            [2, -10, 3, 5],
            [0, 1, 0, -2],
            [2, -1, 1e-5, 1],
            [1, 1, 1, 1],
        ]
    ).flatten()

    constraints = constraints_as_scipy_constraints(problem, n_experiments)

    assert isinstance(constraints[0], NonlinearConstraint)
    assert len(constraints[0].lb) == n_experiments
    assert len(constraints[0].ub) == n_experiments
    assert np.allclose(
        constraints[0].fun(x),
        problem.constraints[0](
            pd.DataFrame(x.reshape(5, 4), columns=["x0", "x1", "x2", "x3"])
        ),
    )


def test_get_jacobian_NChooseK():

    # problem with NChooseK constraint
    inputs = opti.Parameters([opti.Continuous(f"x{i}", [0, 1]) for i in range(4)])
    problem = opti.Problem(
        inputs=inputs,
        outputs=[opti.Continuous("y")],
        constraints=[opti.NChooseK(inputs.names, max_active=2)],
    )
    n_experiments = 5
    D = problem.n_inputs

    x = np.array(
        [
            [1, -10, 2, -1.5],
            [2, -10, 3, 5],
            [0, 1, 0, -2],
            [2, -1, 1e-5, 1],
            [1, 1, 1, 1],
        ]
    ).flatten()

    jac = get_jacobian_NChooseK(problem.constraints[0], problem, n_experiments)

    np.random.seed(1)
    jac_corr = np.array(
        [
            [1, 0, 0, -1],
            [1, 0, 1, 0],
            [0, 0, 0, 0],
            [0, -1, 0, 0],
            [1, 1, 0, 0],
        ]
    )
    J = np.zeros(shape=(n_experiments, D * n_experiments))
    for i in range(n_experiments):
        J[i, i * D : (i + 1) * D] = jac_corr[i]
    assert np.allclose(jac(x), J)

    np.random.seed(100)
    jac_corr = np.array(
        [
            [1, 0, 0, -1],
            [1, 0, 1, 0],
            [0, 0, 0, 0],
            [0, 0, 0, 1],
            [1, 0, 0, 1],
        ]
    )
    J = np.zeros(shape=(n_experiments, D * n_experiments))
    for i in range(n_experiments):
        J[i, i * D : (i + 1) * D] = jac_corr[i]
    assert np.allclose(jac(x), J)

    np.random.seed(200)
    jac_corr = np.array(
        [
            [1, 0, 0, -1],
            [1, 0, 1, 0],
            [0, 0, 0, 0],
            [0, -1, 0, 0],
            [0, 1, 1, 0],
        ]
    )
    J = np.zeros(shape=(n_experiments, D * n_experiments))
    for i in range(n_experiments):
        J[i, i * D : (i + 1) * D] = jac_corr[i]
    assert np.allclose(jac(x), J)