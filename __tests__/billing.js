// These require STRIPE_SECRET_KEY to be set in the STORE instance
import request from "supertest";
import sqlite3 from "sqlite3";
import { jest } from "@jest/globals";

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

import { init, getNewEmail, BASE_URL, API_URL, ETEBASE_URL } from "./helpers";

let db;
let helpers;

jest.setTimeout(10000);

beforeAll(async () => {
  await Etebase.ready;

  db = new sqlite3.Database("../db.sqlite3", sqlite3.OPEN_READWRITE, (err) => {
    if (err) {
      console.error(err.message);
    }
  });

  helpers = init(db);
});

describe.only("create a basic new user", () => {
  let owner;

  const cleanUser = async () => {
    owner = await helpers.signup(getNewEmail());
    await helpers.validate(owner.userReq, owner.userId);
  };

  beforeAll(async () => {
    owner = await helpers.signup(`${Math.random()}@gliff.ai`);
    await helpers.validate(owner.userReq, owner.userId);

    console.log(owner);
  }, 30000);

  describe("billing", () => {
    describe("free trial", () => {
      it("user is on a small plan trial", async () => {
        const { body } = await owner.userReq.get("/billing/plan").expect(200);
        expect(body.tier_id).toBe(2);
        expect(body.trial_end).toBeGreaterThan(body.current_period_start);
      }, 30000);

      it.skip("user can cancel trial", async () => {});

      it("user has an invoice for 0", async () => {
        console.log(owner.userReq._defaults);
        const {
          body: {
            invoices: [invoice],
          },
        } = await owner.userReq.get("/billing/invoices").expect(200);

        expect(invoice.amount_due).toEqual(0);
        expect(invoice.paid).toEqual(true);
      });

      it("user can't addon (as they have no payment details)", async () => {
        await owner.userReq
          .post("/billing/addon/")
          .send({ users: 3 })
          .expect(422, { message: "No valid payment method" });
      });

      // TODO: Maybe test trial ending
    });

    describe("Standard Plans", () => {
      // TODO: Maybe add the actual checkout process with selenium
      it.skip("user create a checkout session to add a payment method", async () => {
        const { body } = await owner.userReq
          .post("/billing/create-checkout-session/")
          .expect(200);

        expect(body.id).toBeDefined();
      });

      it("user can downgrade to free plan", async () => {
        const { body } = await owner.userReq
          .post("/billing/plan/")
          .send({ tier_id: 1 })
          .expect(200);

        expect(body.tier_id).toBe(1);

        // Reset user
        await cleanUser();
      }, 30000);

      it("user can't upgrade without payment", async () => {
        await owner.userReq
          .post("/billing/plan/")
          .send({ tier_id: 3 })
          .expect(422, { message: "No valid payment method" });

        const { body } = await owner.userReq.get("/billing/plan").expect(200);
        expect(body.tier_id).toBe(2);
      });

      it("user can't choose a lower plan than appropriate", async () => {
        const email = getNewEmail();
        const {
          body: { id: invite_id },
        } = await owner.userReq
          .post("/user/invite/")
          .send({ email })
          .expect(200);

        await helpers.signup(email, { team_id: owner.teamId, invite_id });
        await owner.userReq
          .post("/billing/plan/")
          .send({ tier_id: 1 })
          .expect(422, {
            message: "Too many users to switch to this plan",
          });

        const { body } = await owner.userReq.get("/billing/plan").expect(200);
        expect(body.tier_id).toBe(2);
      }, 30000);
    });

    describe("Custom Plans", () => {});

    describe.skip("Invoice Plans", () => {});

    describe.skip("Coupons", () => {});
  });
});
