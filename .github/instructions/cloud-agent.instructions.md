---
applyTo: '**'
excludeAgent: 'code-review'
description: 'Guidelines for GitHub Copilot cloud agent when working in Starcraft.'
---

# GitHub Cloud Agent Instructions for Starcraft

These instructions guide GitHub Copilot cloud agent when it works in Starcraft projects. These don't apply to the initial review provided by GitHub Copilot code review.

## Code changes in pull request comments

These instructions apply to interactions between users and the cloud agent, when they mention it with `@copilot`.

### Draft changes when explicitly requested

When a user mentions `@copilot` in a comment asking to draft or propose a code change, reply in a comment using GitHub's code suggestion syntax. Do not commit directly to the branch.

Examples of requests that should trigger this behavior include:

- "propose a change"
- "show me what this would look like"
- "what would this look like?"
- "can you draft that?"
- "show me an example"
- "write that out"
- "what do you suggest?"
- "show a fix for this"
- "give me a suggestion"
- "how would you write this?"

Reply using GitHub's code suggestion syntax:

````markdown
```suggestion
<proposed code>
```
````

This allows the user to review and apply the suggestion themselves with a single click.

### Only commit changes when explicitly requested

When a user mentions `@copilot` in a comment asking to finalize a code change, commit the change as requested.

If no prior suggestion exists in the current PR conversation, propose the change first using the suggestion syntax above before committing.

Examples of requests that should trigger this behavior include:

- "commit what is proposed"
- "push this code"
- "apply these changes"
- "go ahead and commit"
- "push the changes"
- "commit the suggestion"
- "apply the fix"
- "push what you suggested"
- "land these changes"


### Combined implement and commit requests

If a user asks for a change **and** explicitly requests it be committed in the same message, treat it as an explicit commit request. Implement the change and commit it directly without posting a suggestion first.

Examples of requests that should trigger this behavior include:

- "implement X and push it"
- "fix this and commit"
- "make this change and push"
- "do X and land it"
- "apply X and commit"
- "patch this and commit"
- "commit a fix for this"
