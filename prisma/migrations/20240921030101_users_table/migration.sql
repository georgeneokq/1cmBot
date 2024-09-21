-- CreateTable
CREATE TABLE `users` (
    `id` INTEGER NOT NULL,
    `derivation_path` INTEGER NOT NULL AUTO_INCREMENT,
    `slippage` DOUBLE NOT NULL DEFAULT 0.3,
    `chain_id` VARCHAR(191) NULL,

    UNIQUE INDEX `users_derivation_path_key`(`derivation_path`),
    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
