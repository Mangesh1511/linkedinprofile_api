# 📚 LinkedIn Voyager RESTli API Reference Guide

This document provides a technical specification of LinkedIn's reverse-engineered **Voyager RESTli API** endpoints, request headers, authentication mechanics, and response schemas used in `linkedinprofile_api`.

---

## 🏛️ Protocol & Authentication Specification

LinkedIn's internal frontend communicates with backend microservices using the **RESTli 2.0** protocol.

### 1. Base URL
`https://www.linkedin.com/voyager/api/`

### 2. Mandatory HTTP Request Headers

| Header Key | Value Format | Description |
| :--- | :--- | :--- |
| `csrf-token` | `ajax:1234567890123456789` | Value of `JSESSIONID` cookie stripped of quotes. Required for anti-CSRF validation. |
| `x-restli-protocol-version` | `2.0.0` | Enforces RESTli 2.0 JSON serialization protocol. |
| `x-li-lang` | `en_US` | Sets response localization language. |
| `Accept` | `application/vnd.linkedin.normalized+json+2.0, application/json` | Requests normalized Voyager JSON payload format. |
| `User-Agent` | Standard Chrome/Safari User-Agent | Simulates legitimate web client browser headers. |
| `Cookie` | `li_at=...; JSESSIONID="..."` | Session authentication cookies. |

---

## 📡 Voyager API Endpoints

### 1. Core Profile Information (Dash Profile API)
```http
GET /voyager/api/identity/dash/profiles?q=memberIdentity&memberIdentity={public_slug}
```

#### Purpose
Fetches top-card profile details including name, headline, location, and about summary.

#### Response JSON Schema (Sample)
```json
{
  "elements": [
    {
      "publicIdentifier": "mangesh-dudhgaonkar-patil-422870209",
      "multiLocaleFirstName": { "en_US": "Mangesh" },
      "multiLocaleLastName": { "en_US": "Dudhgaonkar Patil" },
      "headline": "Software Engineer | MongoDB | Java | Spring | MicroServices | AI Integration",
      "locationName": "Pune District, Maharashtra, India",
      "multiLocaleSummary": {
        "en_US": "As an Associate Software Engineer-Backend at Onshape, a PTC Technology..."
      },
      "objectUrn": "urn:li:member:888973658"
    }
  ]
}
```

---

### 2. Work Experiences (Position Groups API)
```http
GET /voyager/api/identity/profiles/{public_slug}/positionGroups
```

#### Purpose
Fetches list of work experiences grouped by company, including job titles, dates, locations, and descriptions.

#### Response JSON Schema (Sample)
```json
{
  "elements": [
    {
      "name": "Onshape, a PTC Technology",
      "positions": [
        {
          "title": "Software Engineer",
          "companyName": "Onshape, a PTC Technology",
          "locationName": "Pune District",
          "timePeriod": {
            "startDate": { "month": 7, "year": 2024 }
          }
        }
      ]
    }
  ]
}
```

---

### 3. Education Details API
```http
GET /voyager/api/identity/profiles/{public_slug}/educations
```

#### Purpose
Fetches educational institutions, degrees, fields of study, and dates.

---

### 4. Endorsed Skills API
```http
GET /voyager/api/identity/profiles/{public_slug}/skills
```

#### Purpose
Fetches listed skills and endorsement counts.

---

## 🗺️ Data Model Mapping Reference

| Voyager JSON Path | Pydantic Model Field |
| :--- | :--- |
| `elements[0].multiLocaleFirstName.en_US` | `Person.name` (First part) |
| `elements[0].multiLocaleLastName.en_US` | `Person.name` (Last part) |
| `elements[0].headline` | `Person.headline` |
| `elements[0].locationName` | `Person.location` |
| `elements[0].multiLocaleSummary.en_US` | `Person.about` |
| `elements[i].positions[j].title` | `Experience.position_title` |
| `elements[i].name` | `Experience.institution_name` |
| `elements[i].positions[j].locationName` | `Experience.location` |
