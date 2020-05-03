from .graph_problem_interface import *
from .utils.timer import Timer
from .utils.heapdict import heapdict
from typing import Optional, Dict, Callable
import abc


class SearchNodesPriorityQueue:
    """
    This class is used as a data structure for the `open` queue in the BestFirstSearch algorithm.
    Notice that we store a mapping from state to the node represents it for quick operations.
    """

    def __init__(self):
        self._nodes_queue = heapdict()  # node -> priority (selecting the next node to expand is done by this score)
        self._state_to_search_node_mapping: Dict[GraphProblemState, SearchNode] = {}

    def has_state(self, state: GraphProblemState) -> bool:
        return state in self._state_to_search_node_mapping

    def get_node_by_state(self, state: GraphProblemState) -> Optional[SearchNode]:
        return self._state_to_search_node_mapping.get(state, None)

    def push_node(self, node: SearchNode):
        assert node.state not in self._state_to_search_node_mapping
        self._nodes_queue[node] = (node.expanding_priority, -node.g_cost, hash(node.state))
        self._state_to_search_node_mapping[node.state] = node

    def pop_next_node(self) -> SearchNode:
        node, _ = self._nodes_queue.popitem()
        del self._state_to_search_node_mapping[node.state]
        return node

    def peek_next_node(self) -> SearchNode:
        node, _ = self._nodes_queue.peekitem()
        return node

    def extract_node(self, node: SearchNode):
        del self._state_to_search_node_mapping[node.state]
        self._nodes_queue.pop(node)

    def is_empty(self) -> bool:
        return self._nodes_queue.empty()

    def __len__(self):
        return len(self._nodes_queue)


class SearchNodesCollection:
    """
    This class is used as a data structure for the `close` set in the BestFirstSearch algorithm.
    Notice that we store a mapping from state to the node represents it for quick operations.
    """

    def __init__(self):
        self._state_to_search_node_mapping: Dict[GraphProblemState, SearchNode] = {}

    def add_node(self, node: SearchNode):
        assert node.state not in self._state_to_search_node_mapping
        self._state_to_search_node_mapping[node.state] = node

    def remove_node(self, node: SearchNode):
        assert node.state in self._state_to_search_node_mapping
        del self._state_to_search_node_mapping[node.state]

    def has_node(self, node: SearchNode) -> bool:
        return node.state in self._state_to_search_node_mapping \
            and node is self._state_to_search_node_mapping[node.state]

    def has_state(self, state: GraphProblemState) -> bool:
        return state in self._state_to_search_node_mapping

    def get_node_by_state(self, state: GraphProblemState) -> Optional[SearchNode]:
        return self._state_to_search_node_mapping.get(state, None)

    def __len__(self):
        return len(self._state_to_search_node_mapping)


class BestFirstSearch(GraphProblemSolver):
    """
    Best First Search is a generic search algorithm, as we learnt in class.
    This algorithm maintains an `open` priority queue during the search.
    The `open` queue stores search nodes (of type SearchNode) created
     during the search.
    As long as the open queue is not empty, the algorithm extract the
     next node from it and expands it.
    Expanding a node is done by iterating over the successor states of the state
     of the expanded node. For each successor state, a dedicated node is created,
     and this node is opened (added to the open queue).
    Notice that, as a generic algorithm, it represents a family of algorithms,
     and hence this is an abstract class. It means that it has abstract methods
     that have to be overridden by the inheritor.
    The priority that a node is associated with in the `open` queue, is not
     determined by this generic algorithm, and have to be defined by the inheritor
     by overriding the abstract method `_calc_node_expanding_priority()`.
    The opening of a successor node is also not defined by this algorithm,
     and have to be defined by the inheritor by overriding the abstract method
     `_open_successor_node()`.
    """

    solver_name: str = 'BestFirstSearch'

    def __init__(self, use_close: bool = True, max_nr_states_to_expand: Optional[int] = None,
                 open_criterion: Optional[Callable[[SearchNode], bool]] = None):
        self.open: SearchNodesPriorityQueue = None
        self.close: Optional[SearchNodesCollection] = None
        self.use_close = use_close
        self.max_nr_states_to_expand = max_nr_states_to_expand
        self.open_criterion = open_criterion
        self.max_nr_stored_states = 0

    def solve_problem(self, problem: GraphProblem) -> SearchResult:
        """
        Implementation of the generic Best First Search algorithm.
        """

        final_search_node = None
        nr_expanded_states = 0
        max_nr_stored_states = 0

        def _get_current_nr_stored_states() -> int:
            return len(self.open) + (len(self.close) if self.close is not None else 0)

        self.open = SearchNodesPriorityQueue()
        if self.use_close:
            self.close = SearchNodesCollection()
        else:
            self.close = None
        self._init_solver(problem)

        with Timer(print_title=False) as timer:
            initial_search_node = SearchNode(
                state=problem.initial_state, parent_search_node=None, operator_cost=problem.get_zero_cost())
            initial_search_node.expanding_priority = self._calc_node_expanding_priority(initial_search_node)
            self.open.push_node(initial_search_node)
            max_nr_stored_states = max(max_nr_stored_states, _get_current_nr_stored_states())

            exceeded_max_nr_expanded_states = False
            while True:
                next_node_to_expand = self._extract_next_search_node_to_expand(problem)
                if next_node_to_expand is None:
                    break
                if problem.is_goal(next_node_to_expand.state):
                    final_search_node = next_node_to_expand
                    break

                if self.max_nr_states_to_expand is not None and nr_expanded_states >= self.max_nr_states_to_expand:
                    exceeded_max_nr_expanded_states = True
                    break

                nr_expanded_states += 1

                # Iterate over next states and perform the update step for each.
                for operator_result in problem.expand_state_with_costs(next_node_to_expand.state):
                    assert isinstance(operator_result, OperatorResult)
                    successor_node = SearchNode(
                        state=operator_result.successor_state,
                        parent_search_node=next_node_to_expand,
                        operator_cost=operator_result.operator_cost,
                        operator_name=operator_result.operator_name)
                    successor_node.expanding_priority = self._calc_node_expanding_priority(successor_node)
                    if self.open_criterion is None or self.open_criterion(successor_node):
                        self._open_successor_node(problem, successor_node)
                    max_nr_stored_states = max(max_nr_stored_states, _get_current_nr_stored_states())

        stop_reason = StopReason.ExceededMaxNrStatesToExpand if exceeded_max_nr_expanded_states \
            else StopReason.CompletedRunSuccessfully
        return SearchResult(
            solver=self,
            problem=problem,
            solution_path=final_search_node.make_states_path() if final_search_node is not None else None,
            nr_expanded_states=nr_expanded_states,
            max_nr_stored_states=max_nr_stored_states,
            solving_time=timer.elapsed,
            stop_reason=stop_reason
        )

    def _init_solver(self, problem: GraphProblem):
        """
        Called once by `solve_problem()` right after creating `open` and `close`.
        This method might be overridden by the inheritor algorithm if needed.
        This method can create and initialize fields of this object, in order
         to be used later by other methods called during the search.
        """

    def _extract_next_search_node_to_expand(self, problem: GraphProblem) -> Optional[SearchNode]:
        """
        Extracts the next node to expand from the open queue.
        This is a default implementation.
        This method might be overridden by the inheritor algorithm if needed.
        """
        if self.open.is_empty():
            return None
        node_to_expand = self.open.pop_next_node()
        if self.use_close:
            self.close.add_node(node_to_expand)
        return node_to_expand

    @abc.abstractmethod
    def _calc_node_expanding_priority(self, search_node: SearchNode) -> float:
        """
        Called by `solve_problem()` whenever just after creating a new successor node.
        Should calculate and return the f-score of the given node.
        This score is used as a priority of this node in the open priority queue.
        """
        ...

    @abc.abstractmethod
    def _open_successor_node(self, problem: GraphProblem, successor_node: SearchNode):
        """
        Called by `solve_problem()` whenever creating a new successor node.
        This method is responsible for adding this just-created successor
         node into the `self.open` priority queue, and may check the existence
         of another node representing the same state in `self.close`.
        """
        ...

