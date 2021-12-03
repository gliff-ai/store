import request from "supertest";
import sqlite3 from "sqlite3";

import Etebase, {
  Account,
  Collection,
  CollectionManager,
  Item,
  ItemManager,
  toBase64,
  OutputFormat,
  CollectionAccessLevel,
} from "etebase";

const { BASE_URL = "http://localhost:8000" } = process.env;

const API_URL = `${BASE_URL}/django/api`;
const ETEBASE_URL = `${BASE_URL}/etebase`;

let db;
let helpers = {};

beforeAll(async () => {
  await Etebase.ready;
});

beforeAll(async () => {
  db = new sqlite3.Database("../db.sqlite3", sqlite3.OPEN_READWRITE, (err) => {
    if (err) {
      console.error(err.message);
    }
    console.log("Connected to the database.");

    helpers.getUserProfile = (id) => {
      return new Promise((resolve) => {
        db.get(
          `SELECT * FROM myauth_userprofile WHERE user_id = "${id}"`,
          (_err, row) => resolve(row)
        );
      });
    };
  });
});

test("Check for test mode", (done) => {
  request(API_URL)
    .get("/")
    .expect(200, '"Hello Test World"')
    .then(() => done())
    .catch((e) => {
      console.log(
        `Healthcheck test failed, is STORE running at ${BASE_URL}? If it is, ensure you are using the test.py settings file`
      );
      console.log(e.message);
      process.exit(1); // Bail hard
      done(true);
    });
});

describe("create a basic new user", () => {
  const email = `${Math.random()}@gliff.ai`;
  let userReq;
  let userId;
  let newEtebaseUser;

  beforeAll(async () => {
    newEtebaseUser = await Account.signup(
      {
        username: toBase64(email),
        email,
      },
      "password",
      ETEBASE_URL
    );

    expect(newEtebaseUser.user.email).toEqual(newEtebaseUser.user.username);

    db.get(
      `SELECT *
           FROM myauth_user 
           WHERE email = "${email}"
           LIMIT 1`,
      (_err, row) => {
        userId = row.id;
      }
    );

    await request(API_URL)
      .post("/user/")
      .set("Content-Type", "application/json")
      .set("Authorization", `Token ${newEtebaseUser.authToken}`)
      .send({
        name: "Test User",
        team_id: null,
        invite_id: null,
        accepted_terms_and_conditions: true,
        recovery_key: "",
      })
      .expect(200);

    userReq = request
      .agent(API_URL)
      .set("Content-Type", "application/json")
      .set("Authorization", `Token ${newEtebaseUser.authToken}`);
  }, 30000);

  afterAll(async () => {
    await userReq.post("/billing/cancel/").expect(422, {
      message: "No valid subscription to cancel. Try changing your plan",
    });
  });

  describe("validate user", () => {
    // We can't really check the email gets sent, but we can do the rest of the process
    test("validate user email", (done) => {
      // Get verification code from db
      db.get(
        `SELECT uid
            FROM main.myauth_emailverification
            WHERE user_profile_id = ${userId}
            LIMIT 1`,
        (err, { uid }) => {
          // "Click" the link
          userReq
            .get(`/user/verify_email/${uid}`)
            .expect(200)
            .end(() => {
              helpers.getUserProfile(userId).then((profile) => {
                expect(profile.email_verified).not.toBeNull();
                done();
              });
            });
        }
      );
    });

    test("the user should be a team owner", async () => {
      const {
        body: { profiles, pending_invites },
      } = await userReq.get("/team/");

      expect(profiles.length).toBe(1);
      expect(pending_invites.length).toBe(0);

      const [profile] = profiles;
      expect(profile.email).toBe(email);
      expect(profile.team.owner_id).toBe(userId);
      expect(profile.team.tier.id).toBe(1);
    });
  });

  describe("billing", () => {
    // TODO fix api
    it.skip("user doesn't have payment method", async () => {
      const { body } = await userReq.get("/billing/payment-method").expect(204);
    });

    // TODO fix api
    it.skip("user doesn't have invoices", async () => {
      const { body } = await userReq.get("/billing/invoices").expect(204);
    });

    it("free user can't get addon prices", async () => {
      await userReq.get("/billing/addon-prices").expect(422);
    });

    it("free user can't addon", async () => {
      await userReq.post("/billing/addon/ ").send({ users: 3 }).expect(422);
    });

    // TODO support this and make the test CAN upgrade
    it("free user can't upgrade", async () => {
      await userReq.post("/billing/create-authd-checkout-session/").expect(422);
    });

    it("user can view limits", async () => {
      await userReq.get("/billing/limits").expect(200, {
        has_billing: false,
        tier_name: "COMMUNITY",
        tier_id: 1,
        users_limit: 1,
        projects_limit: 1,
        collaborators_limit: 2,
        users: 1,
        projects: 0,
        collaborators: 0,
        storage: 0,
        storage_included_limit: 1000,
      });
    });
  });

  describe("free limits", () => {
    const inviteeEmail = `${Math.random()}@gliff.ai`;
    it("fail to send an invite", async () => {
      await userReq
        .post("/user/invite/")
        .send({ email: inviteeEmail })
        .expect(401, { message: "Can't invite a new user, limit is reached" });
    });

    it("create collaborator invite", async () => {
      const {
        body: { id },
      } = await userReq
        .post("/user/invite/collaborator/")
        .send({ email: inviteeEmail })
        .expect(200);
    });

    it("create a project", async () => {
      const collectionManager = newEtebaseUser.getCollectionManager();

      // Create, encrypt and upload a new collection
      const collection = await collectionManager.create(
        "gliff.test.gallery", // type
        {
          name: "Gallery 1",
          createdTime: Date.now(),
          modifiedTime: Date.now(),
          description: "[]",
        }, // metadata
        "[]" // content
      );
      await collectionManager.upload(collection);

      const { data } = await collectionManager.list("gliff.test.gallery");

      expect(data.length).toBe(1);
      expect(data[0].encryptedCollection).toBeDefined();
    });

    it("can't create a 2nd project", async () => {
      const collectionManager = newEtebaseUser.getCollectionManager();

      // Create, encrypt and upload a new collection
      const collection = await collectionManager.create(
        "gliff.test.gallery", // type
        {
          name: "Gallery 2",
          createdTime: Date.now(),
          modifiedTime: Date.now(),
          description: "[]",
        }, // metadata
        "[]" // content
      );

      expect(collectionManager.upload(collection)).rejects.toThrow(
        "Can't create a new project, limit is reached"
      );

      const { data } = await collectionManager.list("gliff.test.gallery");
      expect(data.length).toBe(1);
    });

    // TODO: Other stuff a free user can't do?
  });
});

// TODO Collab

// TODO Team Member

// TODO Paid team (think this just tests limits?)
