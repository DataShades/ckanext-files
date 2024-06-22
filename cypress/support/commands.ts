/// <reference types="cypress" />
// ***********************************************
// This example commands.ts shows you how to
// create various custom commands and overwrite
// existing commands.
//
// For more comprehensive examples of custom
// commands please read more here:
// https://on.cypress.io/custom-commands
// ***********************************************
//
//
// -- This is a parent command --
// Cypress.Commands.add('login', (email, password) => { ... })
//
//
// -- This is a child command --
// Cypress.Commands.add('drag', { prevSubject: 'element'}, (subject, options) => { ... })
//
//
// -- This is a dual command --
// Cypress.Commands.add('dismiss', { prevSubject: 'optional'}, (subject, options) => { ... })
//
//
// -- This will overwrite an existing command --
// Cypress.Commands.overwrite('visit', (originalFn, url, options) => { ... })
//
// declare global {
//   namespace Cypress {
//     interface Chainable {
//       login(email: string, password: string): Chainable<void>
//       drag(subject: string, options?: Partial<TypeOptions>): Chainable<Element>
//       dismiss(subject: string, options?: Partial<TypeOptions>): Chainable<Element>
//       visit(originalFn: CommandOriginalFn, url: string, options: Partial<VisitOptions>): Chainable<Element>
//     }
//   }
// }

Cypress.Commands.add("resetDb", () => {
    cy.exec("yes | ckan -ctest.ini db clean");
    cy.exec("ckan -ctest.ini db upgrade");
});
Cypress.Commands.add("seedUsers", () => {
    for (let name in users) {
        const info = users[name];
        cy.exec(
            `yes | ckan -ctest.ini ${info.sysadmin ? "sysadmin" : "user"} add ${name} password=${info.password} email=${info.email}`,
        );
    }
});

Cypress.Commands.add("login", (user: string = "admin") => {
    cy.session(
        user,
        () => {
            cy.visit("/user/login");
            cy.get("input[name=login]").type(user);
            cy.get("input[name=password]")
                .type(users[user].password)
                .type("{enter}");
            cy.get(".account .username").should("contain", user);
        },
        { cacheAcrossSpecs: true }
    );
});

const users = {
    admin: { password: "password123", sysadmin: true, email: "admin@test.net" },
};


declare namespace Cypress {
    interface Chainable {
        /**
         * Login as a CKAN user.
         *
         * @param {string} user Name of the logged in user. Default to `admin`
         * @example
         *    cy.login()
         *    cy.login("normal_user")
         */
        login(user?: string): Chainable<void>;

        /**
         * Clean and re-initialize the database.
         */
        resetDb(): Chainable<void>;

        /**
         * Create all default user accounts.
         */
        seedUsers(): Chainable<void>;
    }
}
