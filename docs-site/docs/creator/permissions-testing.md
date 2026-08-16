---
title: Permissions and testing
sidebar_label: Permissions and testing
---

# Permissions and testing

An agent's permission manifest is the contract between the creator, the organization, and the runtime. Declare model aliases, data classes, tools, network destinations, storage behavior, and side-effect level explicitly.

## Required test cases

A release should include normal business examples, malformed input, missing context, prompt injection, sensitive data, tool timeout, provider failure, budget exhaustion, unauthorized role, and rollback behavior. Tests should assert both the expected answer and the expected policy decision.

## Evidence

Store test fixtures, expected outputs, policy versions, dependency scan results, and release metadata with the package. Reviewers should be able to reproduce the result without receiving customer secrets.
