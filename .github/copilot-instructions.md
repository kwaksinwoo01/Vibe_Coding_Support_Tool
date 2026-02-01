---
name: Development of MCP toolkit for automatic work plan management
description: This program activates the MCP toolkit packaged as an .exe in your local environment to enable AI coding agents to automatically create, modify, execute and document work plans. "vibeStation_setup" is responsible for installation and initial setup, and the internal directory "vibeStation_setup\mcp_suver" is an application created when installing "vibeStation_setup". 
---

# Dropbox Automation System

**Version**: 2.4.1
**Created**: 2025-11-19
**Updated**: 2026-01-28

---

## 🔧 Work purpose
"vibeStation_setup" is responsible for installing "vibeStation_setup\mcp_suver". The .exe file created with "vibeStation_setup\mcp_suver" supports the MCP Local Server Run tab, allowing AI coding agents to automatically create, modify, execute, and document action plans. "vibeStation_setup\vibeStation_monitor" is a user work plan management support tool. It provides functions for creating, modifying, executing, and documenting work plans by linking with and changing existing work plans.

---

## 🔑 Code development process security

1. **Security environment variable**: The file "vibeStation_setup\mcp_suver\.env" contains sensitive information, so never commit it to your version control system. However, since I need this file in my local development environment, I added it to the .gitignore file and set it to be ignored. Also, be careful not to include this file during the exe packaging process. Even with exe packaging, the program needs the ability to save the user's environment variables, so you must create a separate file to encrypt and save the environment variables.

2. You must disable changes by co-developers:
requirements.txt, .gitignore, .env.example, README.md, .github/workflow/ci-cd.yml

3. Improved method of saving code feedback learning materials:
The database storage method of MCP files is highly compatible and a method suitable for storing large quantities of files must be used. The sqlite method has now been adopted. The database plans to support the ability to save data by specifying a storage path.

---

## 🔧 Required Setup

1. Decide to save the work report in the “docs/ip” folder.
2. Decide to save the work plan in the “docs/wp” folder.
3. Document creation in any other path is prohibited.
4. Supports the ability to automatically create, modify, execute and document work plans in the MCP Local Server Execution tab.
5. Cloud method is not supported.
---

## 🧪 Testing Requirements

---

## 🚫 Critical Constraints


---

## 🌟 Best Practices

---

## 🔗 Domain Service Integration

---

## 📚 Key Documentation

---
