# API Rate Limits

## Overview

This document tracks rate limits for external APIs and data sources used by the project. Test scripts must respect these limits.

## Rate Limit Table

| Service | Rate Limit | Notes |
|---------|-----------|-------|
| [Service Name] | [limit] | [notes] |

## Test Script Guidelines

- Services with rate limits **must** be mocked in unit tests
- Use `unittest.mock` (Python) or equivalent for mocking
- Only public, unauthenticated endpoints may be called in tests
- Rate limit testing should be done in separate scripts, not collected by the test runner
