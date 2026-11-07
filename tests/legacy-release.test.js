const assert = require("node:assert/strict")
const { test } = require("node:test")
const fs = require("node:fs")
const path = require("node:path")
const vm = require("node:vm")

const workflow = fs.readFileSync(
  path.join(__dirname, "../.github/workflows/windows-exe-build.yml"),
  "utf8"
)
const source = workflow
  .match(/          script: \|\n([\s\S]*?)(?=\n      - name:)/)[1]
  .replace(/^ {12}/gm, "")
async function release(
  getRef,
  getTag = async () => ({
    data: { object: { type: "commit", sha: "build-commit" } },
  })
) {
  const calls = []
  const context = {
    context: { repo: { owner: "owner", repo: "repo" }, sha: "build-commit" },
    process: { env: { AAA_VERSION: "1.7.0" } },
    core: { setOutput() {} },
    github: {
      rest: {
        git: { getRef, getTag },
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
