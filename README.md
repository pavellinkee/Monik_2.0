DEX Arbitrage Scanner

Project Overview

DEX Arbitrage Scanner is a professional arbitrage opportunity scanner for decentralized exchanges (DEXs) and DEX aggregators.

The application searches for profitable arbitrage opportunities between supported aggregators, validates each opportunity, calculates the final profit after all costs, and sends verified results to Telegram.

The scanner is designed for continuous autonomous operation on a VPS with high reliability, diagnostics, and fault tolerance.

---

Main Goals

- Find real arbitrage opportunities.
- Calculate net profit after gas costs.
- Support multiple blockchain networks.
- Support multiple DEX aggregators.
- Be reliable during long-term autonomous operation.
- Be easy to configure without modifying the source code.
- Be easily extendable by adding new modules.

---

Architecture Principles

The project follows these mandatory principles:

1. Single Responsibility Principle.
2. Immutable data models.
3. Fail Fast validation.
4. Configuration over hardcoded values.
5. One module — one responsibility.
6. Safe handling of external APIs.
7. Production-ready code quality.

---

Project Modules

- Configuration System
- Scanner Engine
- Aggregator Engine
- Token System
- Validation Pipeline
- Gas Calculator
- Database
- Telegram Notifications
- Diagnostics
- Error Knowledge Base
- Alert Manager
- Health Monitor

---

Configuration

All user-editable settings are stored in:

config/user_config.yaml

This is the only configuration file intended for user modifications.

Internal configuration files are stored inside:

config/internal/

---

Development Rules

Every new module must:

- follow the approved architecture;
- have a single responsibility;
- avoid cyclic dependencies;
- provide clear diagnostics;
- support configuration where appropriate;
- be documented.

---

Reliability

The scanner includes:

- Source Failover System
- Consensus Validator
- Integrity Validator
- API Budget Manager
- Health Monitor
- Diagnostic Reporter
- Automatic configuration validation
- Automatic recovery where possible

---

Output

Only validated opportunities with positive net profit after gas costs are reported.

Each reported opportunity includes:

- Buy aggregator
- Sell aggregator
- Network
- Token
- Test amount
- Gas cost
- Final profit (%)
- Final profit (USDT)
- Best opportunity marker (💎)

---

Project Philosophy

Build once.

Maintain easily.

Never sacrifice reliability for short-term convenience.

Every module should be understandable, testable, and replaceable without affecting the rest of the system.
