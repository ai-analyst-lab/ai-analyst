# Pearson Context — English Language Learning (ELL)
Pearson is a global education company providing digital learning products, assessments, and courseware. Within English Language Learning (ELL), Pearson delivers institutional solutions combining courseware, platforms, and AI tools. Pearson English Portal (PEP) is the central access layer for these solutions.

This repository supports analytics and data analysis related to Pearson English Portal (PEP).

The purpose of this file is to provide Claude with **only the necessary business context** to improve the accuracy, relevance, and caution of analytical outputs.

---

## What is Pearson English Portal (PEP)?

**Pearson English Portal (PEP)** is the central digital platform for Pearson’s institutional English language learning customers.

PEP functions primarily as:
- A **portal and access layer** for ELL products.
- The **main authentication and user management system**.
- Learning platform with native features (class management, assignments and assessments, gradebook, presentation tool, ...). More in the following section (Core User Types).

Learning activity may occur in connected products or directly within PEP.

---

## Core User Types

Typical PEP user roles include:

- **Students** – consume learning content and complete activities  
- **Teachers** – manage classes, assignments, and lesson preparation  
- **Institution Admins** – manage users, licenses, and institution setup  

User role context is essential for correct interpretation of activity data.

---

## ELL Products

These products connect via PEP but produce **different analytical signals**.

- **MyEnglishLab (MEL)**  
  Student practice and assessment platform.  

- **Pearson English Connect (PEC)**  
  Courseware delivery and classroom support platform.  

- **Smart Lesson Generator (SLG)**  
  AI tool for teacher lesson preparation using Pearson courseware.  

- **Speaking Tutor**  
  AI-powered speaking practice for learners.Short, repeatable AI interaction events.

- **TestHub**
  Assessment and testing platform for ELL (e.g. benchmark, level, and certificate-related tests).  
  → Produces test execution and assessment outcome data, not learning engagement.

## Product Access

Access to ELL products is typically granted via **redeemed access codes**:

- Students and teachers redeem access codes in PEP to unlock courseware and digital learning tools.
- Redeemed access codes indicate **entitlement**, not actual usage.
- Some products may become visible in PEP once entitlement is granted, even if never used.

Important exception:
- **TestHub assessments are not activated through standard access code redemption**; they are provisioned at institution level and managed within TestHub.

``