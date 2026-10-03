# Workflows

## Git Workflow

### Branch Strategy
- `main`: Production-ready code
- Feature branches: `feature/short-description`
- Bug fix branches: `fix/short-description`

### Commit Checklist
Before every commit:

1. **Run verification**:
   - Python changes: `[テストコマンド]`
   - Framework changes: `[ビルドコマンド]`
   - Both: run both commands
2. **Check diff**: `git diff --cached` to review staged changes
3. **Check status**: `git status` to ensure only intended files are staged
4. **Never commit secrets**: Verify no API keys, tokens, or credentials in diff
5. **Write commit message**:
   - Prefix: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`
   - Description in Japanese

### Commit Message Format
```
[type]: [日本語の説明]

[Optional detailed explanation]
```

Examples:
- `feat: 新機能の実装`
- `fix: バグ修正`
- `docs: ドキュメント更新`
- `refactor: コード整理`

## Deploy Verification

After deployment:

1. Verify build succeeded
2. Check deployed site is accessible
3. Verify key functionality works
4. Record deployment in task file if applicable
