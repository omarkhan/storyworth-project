Storyworth Voice Recordings
===========================

My attempt at Storyworth's take-home assigment:

> Some Storyworth Memoir storytellers do not take to typing their stories, whether because they are uncomfortable with technology or because they are better speakers than writers.  We want to add a feature to let storytellers record a story by phone.
>
> The storyteller will see a landing page that asks them to enter their phone number (design in Figma below).
>
> Upon submitting their phone number, the storyteller should receive an automated call asking them to record a story.
>
> Once they’ve recorded their story, they should be redirected to a page with an audio player to listen to their recording.


Local development
-----------------

First, install [uv](https://docs.astral.sh/uv/). Then:

    # Install dependencies
    uv sync

    # Run migrations
    uv run ./manage.py migrate

    # Run tests
    uv run pytest


Request flow
------------

### Starting a call

```mermaid
sequenceDiagram
  participant User as User
  participant Backend as Backend
  participant Twilio as Twilio Voice API

  User ->> Backend: GET /
  Backend -->> User: 200 OK<br/>HTML form
  User ->> Backend: POST /<br/>tel=917-555-2368
  Note over Backend: Create Recording
  Backend ->> Twilio: Call 917-555-2368
  Twilio -->> Backend: 200 OK
  Backend -->> User: 302 /recording/:id
  User ->> Backend: GET /recording/:id
  Backend -->> User: 200 OK<br/>Call in progress...
```

### Recording

```mermaid
sequenceDiagram
  participant User as User
  participant Backend as Backend
  participant Twilio as Twilio Voice API

  Note over User: Phone rings, answers call
  Twilio ->> Backend: /recording/:id/call_started
  Backend -->> Twilio: 200 OK<br/>TwiML instructions:<br/>1. Play greeting<br/>2. Record call
  Note over User: Hears greeting, starts recording

  User ->> Backend: GET /recording/:id/status
  Backend -->> User: 200 OK<br/>IN_PROGRESS
  User ->> Backend: Poll for updates...
```

### Ending the call

```mermaid
sequenceDiagram
  participant User as User
  participant Backend as Backend
  participant Twilio as Twilio Voice API

  Note over User: Finishes recording, hangs up
  Twilio ->> Backend: /recording/:id/recording_status_updated<br/>RecordingStatus=completed
  Backend -->> Twilio: 200 OK

  User ->> Backend: GET /recording/:id/status
  Backend -->> User: 200 OK<br/>COMPLETE
  User ->> Backend: GET /recording/:id
  Backend -->> User: 200 OK<br/>Recording complete!<br/><audio src="...">
```
