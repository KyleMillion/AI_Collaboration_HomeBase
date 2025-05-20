# Cursor Tools Suite Guide

This guide provides an overview and usage instructions for the `cursor-tools` suite, an AI team with specialized capabilities available in your PowerShell environment. These tools enhance our collaborative efforts by providing powerful functionalities for web search, repository analysis, browser automation, documentation generation, and GitHub integration.

## 1. Overview

The `cursor-tools` suite is designed to seamlessly integrate advanced AI capabilities into your development workflow. These tools are readily available as your API keys are pre-configured.

**Key Environment Details:**
-   **Configuration Storage:** `~/.cursor-tools/`
-   **Setup Function (for new projects):** `Install-CursorTools`
-   **General Aliases:** `ai-web`, `ai-repo`, `ai-doc`, `ai-browser`, `ai-github`, `ai-youtube` (Note: `ai-youtube` was mentioned as an alias but not detailed with a specific tool; its functionality can be added here if specified).

## 2. Specialized AI Team Members

### 2.1. Perplexity (Web Search)

-   **Purpose:** For real-time information retrieval from the web. Ideal for up-to-date facts, technology updates, current events, or any topic requiring recent information.
-   **Usage:**
    ```powershell
    cursor-tools web "your query"
    ```
-   **Alias:**
    ```powershell
    ai-web "your query"
    ```
-   **Example:**
    ```powershell
    cursor-tools web "latest React hooks documentation"
    ```

### 2.2. Gemini (Repository Analysis)

-   **Purpose:** For in-depth codebase understanding, leveraging a large context window (2M tokens) for repository analysis.
-   **Usage:**
    ```powershell
    cursor-tools repo "your query"
    ```
-   **Alias:**
    ```powershell
    ai-repo "your query"
    ```
-   **Example:**
    ```powershell
    cursor-tools repo "explain the authentication flow in this project"
    ```

### 2.3. Stagehand (Browser Automation)

-   **Purpose:** For automating web browser interactions, useful for testing, data gathering, or performing repetitive web tasks.
-   **Usage:**
    ```powershell
    cursor-tools browser <subcommand> "instructions" --url=<url>
    ```
    *(Note: Specific subcommands for Stagehand should be detailed here if known, e.g., `act`, `check`, `get_info`.)*
-   **Alias:** `ai-browser` (Usage would follow the main command structure)
-   **Example:**
    ```powershell
    cursor-tools browser act "Fill the login form" --url=http://localhost:3000
    ```

### 2.4. Documentation Generation

-   **Purpose:** For automatically creating documentation from any GitHub repository.
-   **Usage:**
    ```powershell
    cursor-tools doc --from-github=username/repo --save-to=path/to/file.md
    ```
-   **Alias:** `ai-doc` (Usage would follow the main command structure)
-   **Example:**
    ```powershell
    cursor-tools doc --from-github=yourusername/your-repo --save-to=./PROJECT_DOCS.md
    ```

### 2.5. GitHub Integration

-   **Purpose:** For interacting with GitHub issues and Pull Requests directly from the command line.
-   **Usage:**
    ```powershell
    cursor-tools github issue <issue_number>
    cursor-tools github pr <pr_number>
    ```
-   **Alias:** `ai-github` (Usage would follow the main command structure)
-   **Example:**
    ```powershell
    cursor-tools github issue 123
    cursor-tools github pr 456
    ```

## 3. Ensuring Tools are "In Working Order"

While this guide documents the tools as understood from your provided information, "in working order" operationally depends on:
1.  The `cursor-tools` suite being correctly installed and configured in your PowerShell environment.
2.  The underlying services for each tool (Perplexity AI, Gemini models, browser automation drivers, GitHub APIs) being accessible and functional.
3.  API keys being valid and having the necessary permissions.

As your AI Partner within this environment, I do not directly execute these `cursor-tools` commands myself. Instead, I will:
-   **Proactively Suggest Usage:** Based on our project needs and the roadmaps, I will suggest when and how these tools can be beneficial.
-   **Help Formulate Queries/Commands:** I can assist in crafting effective queries for `ai-web` or `ai-repo`, or help structure commands for other tools.
-   **Process Outputs:** You can share the outputs from these tools with me, and I will integrate that information into our project context, analysis, and decision-making.

This collaborative approach ensures we leverage the full power of the `cursor-tools` suite effectively. This guide will be updated if more details or tools within the suite are specified. 