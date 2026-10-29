// Exécuté une seule fois, à la création de la base de prod (docker-entrypoint-initdb.d).
// Moindre privilège (ADR-0007, ADR-0008) : l'application LIT la collection « orders » alimentée
// par l'ETL et n'ÉCRIT que dans sa propre collection « api_orders ». Elle ne peut ni modifier
// les données de l'ERP, ni supprimer quoi que ce soit, ni administrer la base.
const dbName = process.env.MONGO_INITDB_DATABASE || "livraison_express";
const appDb = db.getSiblingDB(dbName);

appDb.createRole({
  role: "eligibiliteExpressApp",
  privileges: [
    { resource: { db: dbName, collection: "orders" }, actions: ["find"] },
    {
      resource: { db: dbName, collection: "api_orders" },
      actions: ["find", "insert", "createIndex", "listIndexes"],
    },
  ],
  roles: [],
});

appDb.createUser({
  user: process.env.MONGO_APP_USER,
  pwd: process.env.MONGO_APP_PASSWORD,
  roles: ["eligibiliteExpressApp"],
});

print(`Compte applicatif ${process.env.MONGO_APP_USER} créé sur ${dbName} (droits minimaux).`);
