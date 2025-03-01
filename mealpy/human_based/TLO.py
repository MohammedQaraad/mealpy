#!/usr/bin/env python
# ------------------------------------------------------------------------------------------------------%
# Created by "Thieu Nguyen" at 10:14, 18/03/2020                                                        %
#                                                                                                       %
#       Email:      nguyenthieu2102@gmail.com                                                           %
#       Homepage:   https://www.researchgate.net/profile/Thieu_Nguyen6                                  %
#       Github:     https://github.com/thieu1995                                                        %
#-------------------------------------------------------------------------------------------------------%

import numpy as np
from functools import reduce
from copy import deepcopy
from mealpy.optimizer import Optimizer


class BaseTLO(Optimizer):
    """
        Teaching-Learning-based Optimization (TLO)
    An elitist teaching-learning-based optimization algorithm for solving complex constrained optimization problems(TLO)
        This is my version taken the advantages of numpy np.array to faster handler operations.
    Notes:
        + Remove all third loop
        + Using global best solution
    """

    def __init__(self, problem, epoch=10000, pop_size=100, **kwargs):
        """

        Args:
            problem ():
            epoch (int): maximum number of iterations, default = 10000
            pop_size (int): number of population size, default = 100
            **kwargs ():
        """
        super().__init__(problem, kwargs)
        self.nfe_per_epoch = 2 * pop_size
        self.sort_flag = False

        self.epoch = epoch
        self.pop_size = pop_size

    def evolve(self, epoch):
        """
        Args:
            epoch (int): The current iteration
        """
        pop_new = []
        for idx in range(0, self.pop_size):
            ## Teaching Phrase
            TF = np.random.randint(1, 3)  # 1 or 2 (never 3)
            list_pos = np.array([item[self.ID_POS] for item in self.pop])
            DIFF_MEAN = np.random.rand(self.problem.n_dims) * (self.g_best[self.ID_POS] - TF * np.mean(list_pos, axis=0))
            temp = self.pop[idx][self.ID_POS] + DIFF_MEAN
            pos_new = self.amend_position_faster(temp)
            pop_new.append([pos_new, None])
        pop_new = self.update_fitness_population(pop_new)
        pop_new = self.greedy_selection_population(self.pop, pop_new)

        pop_child = []
        for idx in range(0, self.pop_size):
            ## Learning Phrase
            temp = deepcopy(pop_new[idx][self.ID_POS])
            id_partner = np.random.choice(np.setxor1d(np.array(range(self.pop_size)), np.array([idx])))
            # arr_random = np.random.rand(self.problem.n_dims)
            if self.compare_agent(pop_new[idx], pop_new[id_partner]):
                temp += np.random.rand(self.problem.n_dims) * (pop_new[idx][self.ID_POS] - pop_new[id_partner][self.ID_POS])
            else:
                temp += np.random.rand(self.problem.n_dims) * (pop_new[id_partner][self.ID_POS] - pop_new[idx][self.ID_POS])
            pos_new = self.amend_position_faster(temp)
            pop_child.append([pos_new, None])
        pop_child = self.update_fitness_population(pop_child)
        self.pop = self.greedy_selection_population(pop_new, pop_child)


class OriginalTLO(BaseTLO):
    """
    The original version of: Teaching Learning-based Optimization (TLO)
        Teaching-learning-based optimization: A novel method for constrained mechanical design optimization problems
    This is slower version which inspired from this version:
        https://github.com/andaviaco/tblo
    Notes:
        + Removed the third loop to make it faster
    """

    def __init__(self, problem, epoch=10000, pop_size=100, **kwargs):
        """
        Args:
            problem ():
            epoch (int): maximum number of iterations, default = 10000
            pop_size (int): number of population size, default = 100
            **kwargs ():
        """
        super().__init__(problem, epoch, pop_size, **kwargs)
        self.nfe_per_epoch = 2 * pop_size
        self.sort_flag = False

    def evolve(self, epoch):
        """
        Args:
            epoch (int): The current iteration
        """
        for idx in range(0, self.pop_size):
            ## Teaching Phrase
            TF = np.random.randint(1, 3)  # 1 or 2 (never 3)
            #### Remove third loop here
            list_pos = np.array([item[self.ID_POS] for item in self.pop])
            pos_new = self.pop[idx][self.ID_POS] + np.random.uniform(0, 1, self.problem.n_dims) * \
                      (self.g_best[self.ID_POS] - TF * np.mean(list_pos, axis=0))
            pos_new = self.amend_position_faster(pos_new)
            fit_new = self.get_fitness_position(pos_new)
            if self.compare_agent([pos_new, fit_new], self.pop[idx]):
                self.pop[idx] = [pos_new, fit_new]

            ## Learning Phrase
            id_partner = np.random.choice(np.setxor1d(np.array(range(self.pop_size)), np.array([idx])))

            #### Remove third loop here
            if self.compare_agent(self.pop[idx], self.pop[id_partner]):
                diff = self.pop[idx][self.ID_POS] - self.pop[id_partner][self.ID_POS]
            else:
                diff = self.pop[id_partner][self.ID_POS] - self.pop[idx][self.ID_POS]
            pos_new = self.pop[idx][self.ID_POS] + np.random.uniform(0, 1, self.problem.n_dims) * diff
            pos_new = self.amend_position_faster(pos_new)
            fit_new = self.get_fitness_position(pos_new)
            if self.compare_agent([pos_new, fit_new], self.pop[idx]):
                self.pop[idx] = [pos_new, fit_new]


class ITLO(BaseTLO):
    """
    My version of: Improved Teaching-Learning-based Optimization (ITLO)
    Link:
        An improved teaching-learning-based optimization algorithm for solving unconstrained optimization problems
    Notes:
        + Kinda similar to the paper, but the pseudo-code in the paper is not clear.
    """

    def __init__(self, problem, epoch=10000, pop_size=100, n_teachers=5, **kwargs):
        """
        Args:
            problem ():
            epoch (int): maximum number of iterations, default = 10000
            pop_size (int): number of population size, default = 100
            n_teachers (int): number of teachers in class
            **kwargs ():
        """
        super().__init__(problem, epoch, pop_size, **kwargs)
        self.nfe_per_epoch = 2 * pop_size
        self.n_teachers = n_teachers  # Number of teams / group
        self.n_students = pop_size - n_teachers
        self.n_students_in_team = int(self.n_students / self.n_teachers)
        self.teachers, self.teams = None, None

    def classify(self, pop):
        sorted_pop, best = self.get_global_best_solution(pop)
        teachers = sorted_pop[:self.n_teachers]
        sorted_pop = sorted_pop[self.n_teachers:]
        idx_list = np.random.permutation(range(0, self.n_students))
        teams = []
        for id_teacher in range(0, self.n_teachers):
            group = []
            for idx in range(0, self.n_students_in_team):
                start_index = id_teacher * self.n_students_in_team + idx
                group.append(sorted_pop[idx_list[start_index]])
            teams.append(group)
        return teachers, teams, best

    def initialization(self):
        self.pop = self.create_population(self.pop_size)
        self.teachers, self.teams, self.g_best = self.classify(self.pop)

    def evolve(self, epoch):
        """
        Args:
            epoch (int): The current iteration
        """
        for id_teach, teacher in enumerate(self.teachers):
            team = self.teams[id_teach]
            list_pos = np.array([student[self.ID_POS] for student in self.teams[id_teach]])  # Step 7
            mean_team = np.mean(list_pos, axis=0)
            pop_new = []
            for id_stud, student in enumerate(team):
                if teacher[self.ID_FIT][self.ID_TAR] == 0:
                    TF = 1
                else:
                    TF = student[self.ID_FIT][self.ID_TAR] / teacher[self.ID_FIT][self.ID_TAR]
                diff_mean = np.random.rand() * (teacher[self.ID_POS] - TF * mean_team)  # Step 8

                id2 = np.random.choice(list(set(range(0, self.n_teachers)) - {id_teach}))
                if self.compare_agent(teacher, team[id2]):
                    pos_new = (student[self.ID_POS] + diff_mean) + np.random.rand() * (team[id2][self.ID_POS] - student[self.ID_POS])
                else:
                    pos_new = (student[self.ID_POS] + diff_mean) + np.random.rand() * (student[self.ID_POS] - team[id2][self.ID_POS])
                pos_new = self.amend_position_faster(pos_new)
                pop_new.append([pos_new, None])
            pop_new = self.update_fitness_population(pop_new)
            self.teams[id_teach] = self.greedy_selection_population(team, pop_new)

        for id_teach, teacher in enumerate(self.teachers):
            ef = round(1 + np.random.rand())
            team = self.teams[id_teach]
            pop_new = []
            for id_stud, student in enumerate(team):
                id2 = np.random.choice(list(set(range(0, self.n_students_in_team)) - {id_stud}))
                if self.compare_agent(student, team[id2]):
                    pos_new = student[self.ID_POS] + np.random.rand() * (student[self.ID_POS] - team[id2][self.ID_POS]) + \
                              np.random.rand() * (teacher[self.ID_POS] - ef * team[id2][self.ID_POS])
                else:
                    pos_new = student[self.ID_POS] + np.random.rand() * (team[id2][self.ID_POS] - student[self.ID_POS]) + \
                              np.random.rand() * (teacher[self.ID_POS] - ef * student[self.ID_POS])
                pos_new = self.amend_position_faster(pos_new)
                pop_new.append([pos_new, None])
            pop_new = self.update_fitness_population(pop_new)
            self.teams[id_teach] = self.greedy_selection_population(team, pop_new)

        for id_teach, teacher in enumerate(self.teachers):
            team = self.teams[id_teach] + [teacher]
            team, local_best = self.get_global_best_solution(team)
            self.teachers[id_teach] = local_best
            self.teams[id_teach] = team[1:]

        self.pop = self.teachers + reduce(lambda x, y: x + y, self.teams)
