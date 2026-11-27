/**
 * Morning briefing trigger: pings the GitHub Actions workflow every 15 min.
 *
 * Runs in Google Apps Script (script.google.com) under your own Google
 * account, free, no billing account. Replaces an external cron service:
 * GitHub's own `schedule:` trigger is unreliable for this repo, while a
 * workflow_dispatch API call starts a run immediately.
 *
 * Each ping is a plain dispatch (no `force` input), so the workflow's
 * own gate (tools/manage_pause_state.py) decides SEND or SKIP. Pinging
 * often is therefore safe: it sends at most once a day.
 *
 * Setup: see SETUP.md, "Set up the trigger". This file is kept in the
 * repo for the record only -- nothing in the repo runs it.
 *
 * Script properties (Project Settings > Script properties):
 *   GITHUB_TOKEN  fine-grained token, this repo only, Actions: Read and write
 *   GITHUB_REPO   "<owner>/<repo>", e.g. "octocat/morning-briefing-bot"
 *   GITHUB_REF    branch to run on (optional, default "master")
 */

function pingBriefing() {
  var props = PropertiesService.getScriptProperties();
  var token = props.getProperty('GITHUB_TOKEN');
  var repo = props.getProperty('GITHUB_REPO');
  var ref = props.getProperty('GITHUB_REF') || 'master';
  if (!token || !repo) {
    throw new Error('Set GITHUB_TOKEN and GITHUB_REPO in Script properties.');
  }

  var url = 'https://api.github.com/repos/' + repo +
      '/actions/workflows/morning-briefing.yml/dispatches';
  var response = UrlFetchApp.fetch(url, {
    method: 'post',
    contentType: 'application/json',
    headers: {
      Authorization: 'Bearer ' + token,
      Accept: 'application/vnd.github+json',
      'X-GitHub-Api-Version': '2022-11-28',
    },
    payload: JSON.stringify({ ref: ref }),
    muteHttpExceptions: true,
  });

  var code = response.getResponseCode();
  // GitHub answers 204 No Content on success. Throwing on anything else
  // makes the run show as failed in Apps Script's Executions list, and
  // Google emails you about failed triggers.
  if (code !== 204) {
    throw new Error('GitHub dispatch failed: HTTP ' + code + ' ' + response.getContentText());
  }
}

/** Run once by hand to create the 15-minute trigger (idempotent). */
function installTrigger() {
  ScriptApp.getProjectTriggers().forEach(function (trigger) {
    if (trigger.getHandlerFunction() === 'pingBriefing') {
      ScriptApp.deleteTrigger(trigger);
    }
  });
  ScriptApp.newTrigger('pingBriefing').timeBased().everyMinutes(15).create();
}
