const assert = require("node:assert/strict")
const { test } = require("node:test")
const fs = require("node:fs")
const path = require("node:path")
const vm = require("node:vm")

const workflow = fs.readFileSync(
  path.join(__dirname, "../.github/workflows/windows-exe-build.yml"),
  "utf8"
)

function workflowScript(text, stepName, missingMessage) {
  const escaped = stepName.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")
  const match = text.match(
    new RegExp(
      `^[ \\t]*- name: ${escaped}\\b[\\s\\S]*?^[ \\t]*script:\\s*[|>][+-]?\\n([\\s\\S]*?)(?=\\n[ \\t]*- name:)`,
      "m"
    )
  )
  assert.ok(match, missingMessage)
  const lines = match[1].split("\n")
  const indent = lines.reduce((min, line) => {
    if (!line.trim()) return min
    return Math.min(min, line.match(/^[ \t]*/)[0].length)
  }, Infinity)
  if (!Number.isFinite(indent)) return ""
  return lines.map((line) => line.slice(indent)).join("\n")
}

async function release(
  getRef,
  getTag = async () => ({
    data: { object: { type: "commit", sha: "build-commit" } },
  })
) {
  const source = workflowScript(
    workflow,
    "Create Release",
    "release script not found in windows-exe-build.yml"
  )
  const calls = []
  calls.refs = []
  calls.tags = []
  calls.outputs = []
  const context = {
    context: { repo: { owner: "owner", repo: "repo" }, sha: "build-commit" },
    process: { env: { AAA_VERSION: "1.7.0" } },
    core: { setOutput: (...args) => calls.outputs.push(args) },
    github: {
      rest: {
        git: {
          getRef: (options) => {
            calls.refs.push(options)
            return getRef(options)
          },
          getTag: (options) => {
            calls.tags.push(options)
            return getTag(options)
          },
        },
        repos: {
          createRelease: async (options) => {
            calls.push(options)
            return { data: { upload_url: "upload-url" } }
          },
        },
      },
    },
  }
  await new vm.Script(`(async () => {${source}})()`).runInNewContext(context)
  return calls
}

test("a new legacy release tags the exact build commit and stays non-latest", async () => {
  const calls = await release(async () => {
    throw Object.assign(new Error("missing"), { status: 404 })
  })
  assert.equal(calls[0].target_commitish, "build-commit")
  assert.equal(calls[0].make_latest, "false")
  assert.equal(calls[0].name, "Release v1.7.0")
  assert.equal(calls[0].tag_name, "v1.7.0")
  assert.equal(calls[0].draft, false)
  assert.equal(calls[0].prerelease, false)
  assert.equal(calls.refs[0].ref, "tags/v1.7.0")
  assert.equal(calls.refs[0].owner, "owner")
  assert.equal(calls.refs[0].repo, "repo")
  assert.deepEqual(calls.outputs[0], ["upload_url", "upload-url"])
})

test("a legacy release refuses a tag pointing to a different commit", async () => {
  await assert.rejects(
    release(async () => ({
      data: { object: { type: "commit", sha: "different" } },
    })),
    /does not match build commit/
  )
})

test("matching annotated tags are dereferenced before release creation", async () => {
  const calls = await release(async () => ({
    data: { object: { type: "tag", sha: "annotated" } },
  }))
  assert.equal(calls.length, 1)
  assert.equal(calls.tags[0].tag_sha, "annotated")
})

test("a missing annotated object is not mistaken for a missing tag reference", async () => {
  await assert.rejects(
    release(
      async () => ({ data: { object: { type: "tag", sha: "annotated" } } }),
      async () => {
        throw Object.assign(new Error("missing tag object"), { status: 404 })
      }
    ),
    /missing tag object/
  )
})

test("release script extraction ignores indentation and block style", () => {
  const sample = [
    "    - name: Create Release",
    "      with:",
    "        script: >",
    "          const tag = 1",
    "          return tag",
    "    - name: Upload",
  ].join("\n")
  assert.equal(
    workflowScript(sample, "Create Release", "missing"),
    "const tag = 1\nreturn tag"
  )
})

test("legacy preflight refuses existing releases and propagates authorization errors", async () => {
  const preflight = workflowScript(
    workflow,
    "Check release version is unused",
    "release script not found in windows-exe-build.yml"
  )
  const run = (getReleaseByTag) =>
    new vm.Script(`(async () => {${preflight}})()`).runInNewContext({
      context: { repo: { owner: "owner", repo: "repo" } },
      process: { env: { AAA_VERSION: "1.7.0" } },
      github: { rest: { repos: { getReleaseByTag } } },
    })
  await assert.rejects(
    run(async (args) => {
      assert.equal(args.tag, "v1.7.0")
      return { data: {} }
    }),
    /already exists/
  )
  await run(async () => {
    throw Object.assign(new Error("missing"), { status: 404 })
  })
  await assert.rejects(
    run(async () => {
      throw Object.assign(new Error("denied"), { status: 403 })
    }),
    /denied/
  )
})
