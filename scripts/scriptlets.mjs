// SPDX-License-Identifier: GPL-3.0-or-later
// The transformation follows Brave's public resource format. Originals and
// copyright notices are retained in the upstream source archives.
import fs from 'node:fs';
import {pathToFileURL} from 'node:url';
import path from 'node:path';
const [ubo,brave,out]=process.argv.slice(2);
const module=await import(pathToFileURL(path.resolve(ubo,'src/js/resources/scriptlets.js')));
const {registeredScriptlets}=await import(pathToFileURL(path.resolve(ubo,'src/js/resources/base.js')));
const all=module.builtinScriptlets||registeredScriptlets;
if(!all?.length)throw Error('Missing upstream scriptlet registry');
const names=new Set(all.map(s=>s.name));
for(const s of all)for(const d of s.dependencies||[])if(!names.has(d))throw Error(`Missing dependency ${d}`);
const converted=all.map(s=>({name:s.name,aliases:s.aliases||[],kind:{mime:'application/javascript'},content:Buffer.from(s.fn.toString()).toString('base64'),dependencies:s.dependencies||[],permission:s.requiresTrust?1:0}));
const custom=JSON.parse(fs.readFileSync(path.join(brave,'dist/resources.json'),'utf8'));
fs.writeFileSync(out,JSON.stringify([...custom,...converted]));
console.log(`Assembled ${all.length} uBO scriptlets plus ${custom.length} Brave resources`);
