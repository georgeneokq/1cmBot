/*
  Warnings:

  - You are about to alter the column `chain_id` on the `users` table. The data in that column could be lost. The data in that column will be cast from `VarChar(191)` to `Int`.

*/
-- AlterTable
ALTER TABLE `users` MODIFY `chain_id` INTEGER NULL;
