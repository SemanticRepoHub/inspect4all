# Preliminary Experiments

This directory contains the Proof of Concept (PoC) code and preliminary results and analysis for the experiments conducted during the Feasibility Study and as part of our work. These experiments validate the core technical components or concepts of the **inspect4all** tool.

## Experiments Overview

| # | Experiment | Goal | Key Insight |
|---|------------|------|-------------|
| 1 | [ Baseline Tool Exploration (Inspect4py and ReoSim4Py)](inspect4py-experiment/) | Familiarise and validate inspect4py and RepoSim4Py tools | The full extraction to similarity pipeline is well validated and this work build directly on proven foundations. |
| 2 | [Tool Exploration (inspect4j)](inspect4j-experiment/) | Familiarise with other inspect4py variants (specific experiment with inspect4j to assess suitability for reuse) | inspect4py and inspect4j are highly similar. Their schema compatibility and code reusability mean extraction logic does not need to be written from scratch. |
| 3 | [Parser Suitability (tree-sitter)](treesitter-experiment/) | Assess and evaluate tree sitter for building a common AST layer (tested specifically for java) | Tree sitter provides syntactic uniformity but not semantic abstraction, and its API instability adds engineering risk for little benefit at this scope. |
| 4 | [Language Detection](language-detection/) | Determine which language detection tools and libraries to use | go enry is the main library for language detection and its accuracy removes a source of implementation risk. |
| 5 | [Agentic Metadata Enrichment](agentic-enrichment-experiment/) | Assess feasibility with use of agentic AI on enrichment (e.g. backfilling sparse documentation or docstring) | Agentic metadata enrichment is demonstrated to be feasible and model selection (e.g. frontier versus local open source models) is important for balancing cost and accuracy. |
| 6 | [Agentic Similarity Reranking](agentic-reranker-experiment/) | Assess feasibility of agentic reranking for cross language similarity ranking | Agentic reranking is demonstrated to be highly feasible and enables similarity judgements that cosine similarity alone cannot make. |

## Reproducibility Instructions

To reproduce the results reported in the Feasibility Study, follow the steps below:

### 1. Environment Setup
Each experiment is an independent project managed by uv. Ensure you have Python 3.12+ and Java 17+ installed. This project uses uv for isolated and reproducible environments. Modern Java is required to support the analysis of current repositories such as Spring Boot 3 projects. While the baseline javalang parser has known syntax limitations for modern features, these experiments specifically used Java 17 to identify those gaps for the agentic enrichment and modern parser investigation.

### 2. Running the Experiments
The primary method for reproducing these experiments is through the provided Jupyter Notebooks. To reproduce an experiment, navigate into its specific directory and follow the setup and run instructions in the README within that directory.

### 3. Data & Artifacts
The primary outcomes and visualizations for these experiments are contained directly within the Jupyter Notebooks. While raw output and extracted metadata (e.g. JSON and HTML files) are committed to their respective experiment folders for reference, the results are best verified by reviewing the interactive outputs in the notebooks themselves.
