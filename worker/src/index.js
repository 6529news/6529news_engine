// 6529 NEWS Governance - Cloudflare Worker Proxy
// Receives signed proposals/votes from frontend, creates GitHub Issues
// Token is stored as a Cloudflare secret, never exposed to client

const CORS_HEADERS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
};

const REPO = '6529news/6529news_gov';

export default {
  async fetch(request, env) {
    // Handle CORS preflight
    if (request.method === 'OPTIONS') {
      return new Response(null, { headers: CORS_HEADERS });
    }

    if (request.method !== 'POST') {
      return jsonResponse({ error: 'POST only' }, 405);
    }

    const url = new URL(request.url);

    try {
      const body = await request.json();

      if (url.pathname === '/api/proposal') {
        return await handleProposal(body, env);
      } else if (url.pathname === '/api/vote') {
        return await handleVote(body, env);
      } else if (url.pathname === '/api/close-issue') {
        return await handleCloseIssue(body, env);
      } else {
        return jsonResponse({ error: 'Unknown endpoint' }, 404);
      }
    } catch (e) {
      return jsonResponse({ error: e.message }, 400);
    }
  }
};

async function handleProposal(body, env) {
  const { proposal, signature } = body;

  if (!proposal || !signature) {
    return jsonResponse({ error: 'Missing proposal or signature' }, 400);
  }

  if (!proposal.proposer?.address || !proposal.reason) {
    return jsonResponse({ error: 'Invalid proposal data' }, 400);
  }

  const actionLabels = {
    add: 'ADD WAVE', remove: 'REMOVE WAVE',
    general: 'GENERAL', graphics: 'GRAPHICS',
    governance: 'GOVERNANCE', request: 'REQUEST'
  };
  const label = actionLabels[proposal.action] || proposal.action.toUpperCase();
  const title = `[${label}] ${proposal.waveName || proposal.reason.substring(0, 60)}`;
  const issueBody = '```json\n' + JSON.stringify(proposal, null, 2) + '\n```\n\n' +
    `Signature: \`${signature}\`\n` +
    `Proposer: ${proposal.proposer.handle || proposal.proposer.address}\n` +
    `TDH: ${proposal.proposer.tdh?.toLocaleString()}\n` +
    `Allocated: ${proposal.proposerAllocatedTDH?.toLocaleString()} TDH`;

  const issue = await createGitHubIssue(env.GITHUB_TOKEN, title, issueBody, [proposal.action]);
  return jsonResponse({ success: true, issue: { number: issue.number, html_url: issue.html_url } });
}

async function handleVote(body, env) {
  const { voteData, signature } = body;

  if (!voteData || !signature) {
    return jsonResponse({ error: 'Missing vote data or signature' }, 400);
  }

  if (!voteData.voter || !voteData.proposalId || !voteData.vote) {
    return jsonResponse({ error: 'Invalid vote data' }, 400);
  }

  const title = `[VOTE] ${voteData.proposalId} ${voteData.vote}`;
  const issueBody = '```json\n' + JSON.stringify(voteData, null, 2) + '\n```\n\n' +
    `Signature: \`${signature}\`\n` +
    `Voter: ${voteData.voterHandle || voteData.voter}\n` +
    `TDH: ${voteData.voterTDH?.toLocaleString()}\n` +
    `Allocated: ${voteData.allocatedTDH?.toLocaleString()} TDH`;

  const issue = await createGitHubIssue(env.GITHUB_TOKEN, title, issueBody, ['vote']);
  return jsonResponse({ success: true, issue: { number: issue.number, html_url: issue.html_url } });
}

async function handleCloseIssue(body, env) {
  const { issueNumber, address } = body;
  if (!issueNumber || !address) {
    return jsonResponse({ error: 'Missing issueNumber or address' }, 400);
  }

  // Fetch the issue to verify the closer is the proposer
  const issueRes = await fetch(`https://api.github.com/repos/${REPO}/issues/${issueNumber}`, {
    headers: { 'Authorization': `Bearer ${env.GITHUB_TOKEN}`, 'User-Agent': '6529news-gov-worker', 'Accept': 'application/vnd.github+json' }
  });
  if (!issueRes.ok) return jsonResponse({ error: 'Issue not found' }, 404);

  const issue = await issueRes.json();
  const bodyText = issue.body || '';
  // Check that the address appears in the proposal JSON as proposer
  if (!bodyText.toLowerCase().includes(address.toLowerCase())) {
    return jsonResponse({ error: 'Only the proposer can delete their proposal' }, 403);
  }

  // Close the issue
  const closeRes = await fetch(`https://api.github.com/repos/${REPO}/issues/${issueNumber}`, {
    method: 'PATCH',
    headers: { 'Authorization': `Bearer ${env.GITHUB_TOKEN}`, 'Content-Type': 'application/json', 'User-Agent': '6529news-gov-worker', 'Accept': 'application/vnd.github+json' },
    body: JSON.stringify({ state: 'closed', labels: ['withdrawn'] })
  });

  if (!closeRes.ok) {
    const err = await closeRes.json();
    return jsonResponse({ error: err.message || 'Failed to close' }, 500);
  }

  return jsonResponse({ success: true });
}

async function createGitHubIssue(token, title, body, labels) {
  const res = await fetch(`https://api.github.com/repos/${REPO}/issues`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
      'Accept': 'application/vnd.github+json',
      'User-Agent': '6529news-gov-worker'
    },
    body: JSON.stringify({ title, body, labels })
  });

  if (!res.ok) {
    const err = await res.json();
    throw new Error(`GitHub: ${err.message || res.status}`);
  }

  return res.json();
}

function jsonResponse(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json', ...CORS_HEADERS }
  });
}
