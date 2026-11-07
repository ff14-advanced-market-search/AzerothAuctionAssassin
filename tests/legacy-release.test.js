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
  const match = text
    .replace(/\r\n/g, "\n")
    .match(
      new RegExp(
        `^[ \\t]*- name: ${escaped}\\b[\\s\\S]*?^[ \\t]*script:\\s*([|>])[+-]?\\n([\\s\\S]*?)(?=\\n[ \\t]*- name:)`,
        "m"
      )
    )
  assert.ok(match, missingMessage)
  assert.notEqual(
    match[1],
    ">",
    "folded YAML block scalars are not extracted; use script: |"
  )
  const lines = match[2].split("\n")
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

test("release script extraction ignores literal block indentation", () => {
  const sample = [
    "    - name: Create Release",
    "      with:",
    "        script: |",
    "          const tag = 1",
    "          return tag",
    "    - name: Upload",
  ].join("\n")
  assert.equal(
    workflowScript(sample, "Create Release", "missing"),
    "const tag = 1\nreturn tag"
  )
})

test("release script extraction rejects a folded block", () => {
  const sample = [
    "    - name: Create Release",
    "      with:",
    "        script: >",
    "          const tag = 1",
    "    - name: Upload",
  ].join("\n")
  assert.throws(
    () => workflowScript(sample, "Create Release", "missing"),
    /folded YAML block scalars are not extracted/
  )
})

test("legacy preflight runs before the Windows build", () => {
  const preflight = workflow.indexOf("- name: Check release version is unused")
  const build = workflow.indexOf("- name: Build EXE")
  const job = workflow.indexOf("  build-windows:")
  assert.notEqual(preflight, -1)
  assert.notEqual(build, -1)
  assert.ok(preflight < build, "release preflight must run before Build EXE")
  assert.match(workflow.slice(job, preflight), /permissions:\s+contents: write/)
  assert.match(workflow, /^permissions:\n {2}contents: read\n/m)
  assert.equal(workflow.match(/persist-credentials: false/g).length, 2)
  const mac = workflow.indexOf("  build-mac:")
  assert.match(
    workflow.slice(mac, mac + 180),
    /permissions:\n {6}contents: write/
  )
})

test("a legacy release propagates non-404 tag lookup errors", async () => {
  await assert.rejects(
    release(async () => {
      throw Object.assign(new Error("server error"), { status: 500 })
    }),
    /server error/
  )
})

test("nested annotated tags are dereferenced to the build commit", async () => {
  const calls = await release(
    async () => ({ data: { object: { type: "tag", sha: "outer" } } }),
    async ({ tag_sha }) => {
      if (tag_sha === "outer") {
        return { data: { object: { type: "tag", sha: "inner" } } }
      }
      return { data: { object: { type: "commit", sha: "build-commit" } } }
    }
  )
  assert.equal(calls.length, 1)
  assert.deepEqual(
    calls.tags.map((call) => call.tag_sha),
    ["outer", "inner"]
  )
})

test("legacy preflight refuses draft releases and propagates list errors", async () => {
  const preflight = workflowScript(
    workflow,
    "Check release version is unused",
    "release script not found in windows-exe-build.yml"
  )
  const run = (releases) =>
    new vm.Script(`(async () => {${preflight}})()`).runInNewContext({
      context: { repo: { owner: "owner", repo: "repo" } },
      process: { env: { AAA_VERSION: "1.7.0" } },
      github: {
        paginate: async (method, args) => {
          assert.equal(method, "listReleases")
          assert.equal(args.owner, "owner")
          assert.equal(args.repo, "repo")
          assert.equal(args.per_page, 100)
          if (releases instanceof Error) throw releases
          return releases
        },
        rest: { repos: { listReleases: "listReleases" } },
      },
    })
  await assert.rejects(
    run([{ tag_name: "v1.7.0", draft: true }]),
    /already exists/
  )
  await run([{ tag_name: "v1.6.0", draft: false }])
  await assert.rejects(
    run(Object.assign(new Error("denied"), { status: 403 })),
    /denied/
  )
})

test("release script extraction accepts CRLF workflow text", () => {
  const sample = [
    "    - name: Create Release",
    "      with:",
    "        script: |",
    "          const tag = 1",
    "    - name: Upload",
  ].join("\r\n")
  assert.equal(
    workflowScript(sample, "Create Release", "missing"),
    "const tag = 1"
  )
})
