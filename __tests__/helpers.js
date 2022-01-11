import request from "supertest";
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

const init = (db) => {
  const getUserProfile = (id) => {
    return new Promise((resolve) => {
      db.get(
        `SELECT * FROM myauth_userprofile WHERE user_id = "${id}"`,
        (_err, row) => resolve(row)
      );
    });
  };

  const signup = async function (email, team_id = null, invite_id = null) {
    const etebaseUser = await Account.signup(
      {
        username: toBase64(email),
        email,
      },
      "password",
      ETEBASE_URL
    );

    let userId;
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
      .set("Authorization", `Token ${etebaseUser.authToken}`)
      .send({
        name: "Test User",
        team_id,
        invite_id,
        accepted_terms_and_conditions: true,
        recovery_key: "",
      })
      .expect(200);

    const userReq = request
      .agent(API_URL)
      .set("Content-Type", "application/json")
      .set("Authorization", `Token ${etebaseUser.authToken}`);
    return { etebaseUser, userReq, userId, email };
  };

  const validate = (userReq, userId) =>
    new Promise((resolve) => {
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
              getUserProfile(userId).then(({ email_verified }) => {
                expect(email_verified).not.toBeNull();
                resolve();
              });
            });
        }
      );
    });

  return { getUserProfile, validate, signup };
};

export { init, BASE_URL, API_URL, ETEBASE_URL };
