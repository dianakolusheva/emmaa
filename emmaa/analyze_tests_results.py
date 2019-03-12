import json
import logging
from collections import defaultdict
from util import (find_latest_s3_files, find_latest_s3_file,
                  find_second_latest_s3_file, load_test_results_from_s3)
from indra.statements.statements import Statement
from indra.assemblers.english.assembler import EnglishAssembler

CONTENT_TYPE_FUNCTION_MAPPING = {
    'statements': ('get_stmt_ids', 'get_english_statement_by_id'),
    'applied_tests': ('get_applied_test_ids', 'get_english_test_by_id'),
    'passed_tests': ('get_passed_test_ids', 'get_english_test_by_id'),
    'paths': ('get_passed_test_ids', 'get_path_by_id')
}


class TestRound(object):
    def __init__(self, key):
        self.key = key
        self.test_results = load_test_results_from_s3(key)
        self.function_mapping = CONTENT_TYPE_FUNCTION_MAPPING

    # Model Summary
    def get_stmt_id(self, stmt):
        return str(stmt['id'])

    def get_total_statements(self):
        return self.test_results[0]['number_of_statements']

    def get_statements(self):
        return self.test_results[0]['statements']

    def get_stmt_ids(self):
        return [self.get_stmt_id(stmt) for stmt in self.get_statements()]

    def get_statement_types(self):
        statement_types = defaultdict(int)
        for stmt in self.get_statements():
            statement_types[stmt['type']] += 1
        return sorted(statement_types.items(), key=lambda x: x[1], reverse=True)

    def get_agent_distribution(self):
        agent_count = defaultdict(int)
        agent_types = ['subj', 'obj', 'sub', 'enz', 'agent']

        def get_agent_name(stmt, agent_type):
            return stmt[agent_type]['name']

        for stmt in self.get_statements():
            for agent_type in agent_types:
                if agent_type in stmt.keys():
                    agent_count[get_agent_name(stmt, agent_type)] += 1
            if 'members' in stmt.keys():
                for member in stmt['members']:
                    agent_count[member['name']] += 1
        return sorted(agent_count.items(), key=lambda x: x[1], reverse=True)

    def get_statements_by_evidence(self):
        stmts_evidence = {}
        for stmt in self.get_statements():
            stmts_evidence[self.get_stmt_id(stmt)] = len(stmt.evidence)
        return sorted(stmts_evidence.items(), key=lambda x: x[1], reverse=True)

    def get_english_statements(self):
        stmts_by_id = {}
        for stmt in self.get_statements():
            standard_stmt = Statement._from_json(stmt)
            ea = EnglishAssembler([standard_stmt])
            stmts_by_id[self.get_stmt_id(stmt)] = ea.make_model()
        return stmts_by_id

    def get_english_statement_by_id(self, stmt_id):
        return self.get_english_statements[stmt_id]

    # Test Summary
    def has_path(self, result):
        return result['result_json']['path_found']

    def get_test_id(self, result):
        return str(result['test_json']['id'])

    def get_applied_test_ids(self):
        return [self.get_test_id for result in self.test_results[1:]]

    def get_total_applied_tests(self):
        return len(self.test_results)-1

    def get_number_passed_tests(self):
        return len(self.get_passed_test_ids)

    def passed_over_total(self):
        return self.get_number_passed_tests()/self.get_total_applied_tests()

    def get_english_tests(self):
        tests_by_id = {}
        for result in self.test_results[1:]:
            tests_by_id[self.get_test_id(result)] = result['english_test']
        return tests_by_id

    def get_english_test_by_id(self, test_id):
        return self.get_english_tests[test_id]

    def get_passed_test_ids(self):
        passed_tests = []
        for result in self.test_results[1:]:
            if self.has_path(result):
                passed_tests.append(self.get_test_id(result))
        return passed_tests

    def get_path_descriptions(self):
        paths = {}
        for result in self.test_results[1:]:
            if self.has_path(result):
                paths[self.get_test_id(result)] = result['english_result']
        return paths

    def get_path_by_id(self, test_id):
        return self.get_path_descriptions[test_id]

    # Deltas
    def find_numeric_delta(self, other_round, one_round_numeric_func):
        # return self.one_round_func() - other_round.one_round_numeric_func()
        return getattr(self, one_round_numeric_func)()
                       - getattr(other_round, one_round_numeric_func)()

    # def find_stmts_delta(self, other_round):
    #     latest_ids = self.get_stmt_ids()
    #     previous_ids = other_round.get_stmt_ids()
    #     added_ids = list(set(latest_ids) - set(previous_ids))
    #     removed_ids = list(set(previous_ids) - set(latest_ids))
    #     added_stmts = [self.get_english_statement_by_id(stmt_id) 
    #                    for stmt_id in added_ids]
    #     removed_stmts = [other_round.get_english_statement_by_id(stmt_id)
    #                      for stmt_id in removed_ids]
    #     return {'added_stmts': added_stmts, 'removed_stmts': removed_stmts}

    # def find_applied_tests_delta(self, other_round):
    #     latest_test_ids = self.get_applied_test_ids()
    #     previous_test_ids = other_round.get_applied_test_ids()
    #     added_test_ids = list(set(latest_test_ids) - set(previous_test_ids))
    #     removed_test_ids = list(set(previous_test_ids) - set(latest_test_ids))
    #     added_tests = [self.get_english_test_by_id(test_id)
    #                    for test_id in added_test_ids]
    #     removed_tests = [other_round.get_english_test_by_id(test_id)
    #                      for test_id in removed_test_ids]
    #     return {'added_tests': added_tests, 'removed_tests': removed_tests}

    # def find_pass_fail_delta(self, other_round):
    #     latest_passed_ids = self.get_passed_test_ids()
    #     previous_passed_ids = other_round.get_passed_test_ids()
    #     new_passed_ids = list(set(latest_passed_ids) - set(previous_passed_ids))
    #     new_failed_ids = list(set(previous_passed_ids) - set(latest_passed_ids))
    #     new_passed_tests = [self.get_english_test_by_id(test_id)
    #                         for test_id in new_passed_ids]
    #     new_failed_tests = [other_round.get_english_test_by_id(test_id)
    #                         for test_id in new_failed_ids]
    #     return {'new_passed_tests': new_passed_tests, 
    #             'new_failed_tests': new_failed_tests}

    # def find_new_paths(self, other_round):
    #     latest_passed_ids = self.get_passed_test_ids()
    #     previous_passed_ids = other_round.get_passed_test_ids()
    #     new_passed_ids = list(set(latest_passed_ids) - set(previous_passed_ids))
    #     new_failed_ids = list(set(previous_passed_ids) - set(latest_passed_ids))
    #     new_paths = [self.get_path_by_id(test_id) for test_id in new_passed_ids]
    #     old_paths_for_now_failed_tests = 
    #         [other_round.get_path_by_id(test_id) for test_id in new_failed_ids]

    def find_content_delta(self, other_round, content_type):
        """content_type: statements, applied_tests, passed_tests, paths
        """
        latest_ids = getattr(self, self.function_mapping[content_type][0])()
        previous_ids = getattr(other_round,
                               other_round.function_mapping[content_type][0])()
        added_ids = list(set(latest_ids) - set(previous_ids))
        removed_ids = list(set(previous_ids) - set(latest_ids))
        added_items = [getattr(
            self, self.function_mapping[content_type][1])(item_id)
            for item_id in added_ids]
        removed_items = [getattr(
            other_round,
            other_round.function_mapping[content_type][1])(item_id)
            for item_id in removed_ids]
        return {'added': added_items, 'removed': removed_items}


class StatsGenerator(object):
    def __init__(self, model_name, number_of_rounds=10):
        self.model_name = model_name
        self.number_of_rounds = number_of_rounds
        self.latest_round = TestRound(find_latest_s3_file(
            'emmaa', f'results/{model_name}/results_', extension='.json'))
        self.previous_round = TestRound(find_second_latest_s3_file(
            'emmaa', f'results/{model_name}/results_', extension='.json'))
        self.json_stats = {}

    def make_model_summary(self):
        json_stats['model_summary'] = {
            'model_name': model_name,
            'number_of_statements': self.latest_round.get_total_statements(),
            'stmts_type_distr': self.latest_round.get_statement_types(),
            'agent_distr': self.latest_round.get_agent_distribution(),
            'stmts_by_evidence': self.latest_round.get_statements_by_evidence(),
            'english_stmts': self.latest_round.get_english_statements()
        }

    def make_test_summary(self):
        json_stats['test_round_summary'] = {
            'number_applied_tests': self.latest_round.get_total_applied_tests(),
            'number_passed_tests': self.latest_round.get_number_passed_tests(),
            'passed_ratio': self.latest_round.passed_over_total(),
            'tests_by_id': self.latest_round.get_english_test_by_id(),
            'passed_tests': self.latest_round.get_passed_test_ids(),
            'paths': self.latest_round.get_path_descriptions()
        }

    def make_model_delta(self):
        json_stats['model_delta'] = {
            'number_of_statements_delta': self.latest_round.find_numeric_delta(
                self.previous_round, 'get_total_statements'),
            'statements_delta': self.latest_round.find_content_delta(
                self.previous_round, 'statements')
        }

    def make_tests_delta(self):
        json_stats['tests_delta'] = {
            'number_applied_tests_delta': self.latest_round.find_numeric_delta(
                self.previous_round, 'get_total_applied_tests'),
            'number_passed_tests_delta': self.latest_round.find_numeric_delta(
                self.previous_round, 'get_number_passed_tests'),
            'passed_ratio_delta': self.latest_round.find_numeric_delta(
                self.previous_round, 'passed_over_total'),
            'applied_tests_delta': self.latest_round.find_content_delta(
                self.previous_round, 'applied_tests')
            'pass_fail_delta': self.latest_round.find_content_delta(
                self.previous_round, 'passed_tests'),
            'new_paths': self.latest_round.find_content_delta(
                self.previous_round, 'paths')
        }