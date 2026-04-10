# R&D Strategy Agent

An agent-based system that collects recent semiconductor R&D information on HBM4, PIM, and CXL, analyzes competitor technology maturity and threat level, and generates a structured strategy report for R&D decision-makers.

## Overview

- Objective :
  Collect recent evidence from papers, reports, company announcements, and web sources to generate a grounded semiconductor R&D strategy analysis report.
- Method :
  Centralized supervisor-based multi-agent workflow with competitor discovery, web retrieval, RAG retrieval, draft generation, validation, and formatting.
- Tools :
  LangGraph, LangChain, OpenAI API, FAISS, PyMuPDF, Python

## Features

- PDF 자료 기반 정보 추출 (논문, 리포트, 기업 발표문서 등)
- Web Search 기반 최신 정보 수집
- 경쟁사 후보 탐색 및 선정 근거 정리
- 기술 성숙도(TRL 또는 유사 기준) 추정
- 경쟁사별 위협 수준 비교
- 구조화된 기술 전략 보고서 생성
- 검증 및 재실행(Reflection / Validation Loop)
- 확증 편향 방지 전략 :
  - Query Diversification
  - Multi-perspective Retrieval
  - Contradictory Evidence Enforcement
  - Evidence Balance Validation
  - Supervisor Bias Control

## Tech Stack

| Category  | Details                                        |
| --------- | ---------------------------------------------- |
| Framework | LangGraph, LangChain, Python                   |
| LLM       | OpenAI API                                     |
| Retrieval | FAISS, RAG Pipeline                            |
| Embedding | 추후 확정 (예: multilingual-e5-large / bge-m3) |
| Parsing   | PyMuPDF                                        |
| Env Mgmt  | uv                                             |

## Agents

- Supervisor: 전체 Workflow 제어, Agent 호출, rollback 및 termination 결정
- Competitor Discovery Agent: 기술별 경쟁사 후보 탐색 및 선정
- Web Search Agent: 최신 뉴스, 기업 발표, 보도자료 등 웹 정보 수집
- RAG Agent: 논문, 리포트, 특허, 기술 문서 기반 정밀 검색
- Draft Generation Agent: 수집 근거 기반 보고서 초안 생성
- Review / Validation Agent: 근거성, 완결성, 일관성, 실행 가능성 검증
- Formatting Node: 최종 보고서 형식 정리

## Architecture

(그래프 이미지 삽입 예정)

## Directory Structure

```text
├── data/                  # PDF 문서, 리포트, 기사 원문 등 입력 데이터
├── agents/                # Agent 모듈
├── prompts/               # 프롬프트 템플릿
├── outputs/               # 평가 결과 및 보고서 저장
├── app.py                 # 실행 스크립트
└── README.md
```
