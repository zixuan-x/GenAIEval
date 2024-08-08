#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2024 Intel Corporation
# SPDX-License-Identifier: Apache-2.0


import argparse
import json
import os

from evals.evaluation.rag_eval import Evaluator
from evals.evaluation.rag_eval.template import CRUDTemplate


class CRUD_Evaluator(Evaluator):
    def get_ground_truth_text(self, data: dict):
        if self.task == "summarization":
            ground_truth_text = data["summary"]
        elif self.task == "question_answering":
            ground_truth_text = data["answers"]
        elif self.task == "continuation":
            ground_truth_text = data["continuing"]
        elif self.task == "hallucinated_modified":
            ground_truth_text = data["hallucinatedMod"]
        else:
            raise NotImplementedError(
                f"Unknown task {self.task}, only support "
                "summarization, question_answering, continuation and hallucinated_modified."
            )
        return ground_truth_text

    def get_query(self, data: dict):
        if self.task == "summarization":
            query = data["text"]
        elif self.task == "question_answering":
            query = data["questions"]
        elif self.task == "continuation":
            query = data["beginning"]
        elif self.task == "hallucinated_modified":
            query = data["newsBeginning"]
        else:
            raise NotImplementedError(
                f"Unknown task {self.task}, only support "
                "summarization, question_answering, continuation and hallucinated_modified."
            )
        return query

    def get_document(self, data: dict):
        if self.task == "summarization":
            document = data["text"]
        elif self.task == "question_answering":
            document = data["news1"]
        elif self.task == "continuation":
            document = data["beginning"]
        elif self.task == "hallucinated_modified":
            document = data["newsBeginning"]
        else:
            raise NotImplementedError(
                f"Unknown task {self.task}, only support "
                "summarization, question_answering, continuation and hallucinated_modified."
            )
        return document

    def get_template(self):
        if self.task == "summarization":
            template = CRUDTemplate.get_summarization_template()
        elif self.task == "question_answering":
            template = CRUDTemplate.get_question_answering_template()
        elif self.task == "continuation":
            template = CRUDTemplate.get_continuation_template()
        else:
            raise NotImplementedError(
                f"Unknown task {self.task}, only support "
                "summarization, question_answering, continuation and hallucinated_modified."
            )
        return template

    def post_process(self, result):
        return result.split("<response>")[-1].split("</response>")[0].strip()


def args_parser():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--service_url", type=str, default="http://localhost:8888/v1/chatqna", help="Service URL address."
    )
    parser.add_argument("--output_dir", type=str, default="./output", help="Directory to save evaluation results.")
    parser.add_argument(
        "--temperature", type=float, default=0.1, help="Controls the randomness of the model's text generation"
    )
    parser.add_argument(
        "--max_new_tokens", type=int, default=1280, help="Maximum number of new tokens to be generated by the model"
    )
    parser.add_argument(
        "--chunk_size", type=int, default=256, help="the maximum number of characters that a chunk can contain"
    )
    parser.add_argument(
        "--chunk_overlap",
        type=int,
        default=100,
        help="the number of characters that should overlap between two adjacent chunks",
    )
    parser.add_argument("--dataset_path", default="../data/split_merged.json", help="Path to the dataset")
    parser.add_argument("--docs_path", default="../data/80000_docs", help="Path to the retrieval documents")

    # Retriever related options
    parser.add_argument("--tasks", default=["question_answering"], nargs="+", help="Task to perform")
    parser.add_argument("--ingest_docs", action="store_true", help="Whether to ingest documents to vector database")
    parser.add_argument(
        "--database_endpoint", type=str, default="http://localhost:6007/v1/dataprep", help="Service URL address."
    )
    parser.add_argument(
        "--embedding_endpoint", type=str, default="http://localhost:6000/v1/embeddings", help="Service URL address."
    )
    parser.add_argument(
        "--retrieval_endpoint", type=str, default="http://localhost:7000/v1/retrieval", help="Service URL address."
    )
    parser.add_argument("--llm_endpoint", type=str, default=None, help="Service URL address.")
    parser.add_argument(
        "--show_progress_bar", action="store", default=True, type=bool, help="Whether to show a progress bar"
    )
    parser.add_argument("--contain_original_data", action="store_true", help="Whether to contain original data")

    args = parser.parse_args()
    return args


def main():
    args = args_parser()
    if os.path.isfile(args.dataset_path):
        with open(args.dataset_path) as f:
            all_datasets = json.load(f)
    else:
        raise FileNotFoundError(f"Evaluation dataset file {args.dataset_path} not exist.")
    os.makedirs(args.output_dir, exist_ok=True)
    for task in args.tasks:
        if task == "question_answering":
            dataset = all_datasets["questanswer_1doc"]
        elif task == "summarization":
            dataset = all_datasets["event_summary"]
        else:
            raise NotImplementedError(
                f"Unknown task {task}, only support "
                "summarization, question_answering, continuation and hallucinated_modified."
            )
        output_save_path = os.path.join(args.output_dir, f"{task}.json")
        evaluator = CRUD_Evaluator(
            dataset=dataset, output_path=output_save_path, task=task, llm_endpoint=args.llm_endpoint
        )
        if args.ingest_docs:
            CRUD_Evaluator.ingest_docs(args.docs_path, args.database_endpoint, args.chunk_size, args.chunk_overlap)
        results = evaluator.evaluate(
            args, show_progress_bar=args.show_progress_bar, contain_original_data=args.contain_original_data
        )
        print(f"Evaluation results of task {task} saved to {output_save_path}.")


if __name__ == "__main__":
    main()
