// O código de emparelhamento: 6 dígitos, iguais aos que o PC mostra em
// Definições → Controlo remoto.
//
// Vive num módulo só dele, sem imports, porque **três** ficheiros precisam
// destas regras e nenhum pode importar os outros: o `store/remote.ts` valida
// antes de ligar, o `RemoteScreen` limita o campo, e os dois clientes
// (WebSocket e BLE) recusam ligar sem código completo. Se a regra ficasse no
// store, o `remoteClient.ts` teria de o importar — e o store já importa o
// cliente, o que é um ciclo.
//
// Antes disto era um `token` de 16 caracteres hexadecimais: entrava nos dois
// transportes e o PC comparava-o com `==`, sem limite de tentativas. Com 6
// dígitos, quem valida o formato aqui e quem limita as tentativas estão em
// lados diferentes, e nenhum dos dois chega perto de ser o suficiente sozinho:
// isto garante que o que sai do campo é um código, não que seja o certo.

/** Quantos dígitos tem o código. O mesmo número está no PC (`CODE_LEN`). */
export const CODE_LEN = 6;

const CODE_RE = /^\d{6}$/;

/**
 * O código como o utilizador o escreve, já normalizado.
 *
 * O teclado do telemóvel tem acentos e o `paste` traz espaços: limpar aqui é
 * o que faz `"123 456"` e `"123456"` serem o mesmo código. Cortar em 6 é o
 * que impede que um valor colado de outra app encha o campo.
 */
export function normalizeCode(value: unknown): string {
  return String(value ?? '')
    .replace(/\D/g, '')
    .slice(0, CODE_LEN);
}

/** True se já há um código completo para tentar ligar. */
export function codeCompleto(value: unknown): boolean {
  return CODE_RE.test(normalizeCode(value));
}

/**
 * O que dizer ao utilizador quando o `auth` foi recusado.
 *
 * Vive aqui e não em cada cliente porque os dois precisam da mesma frase, e
 * duas cópias divergem: o `auth_locked` só existe desde o código de 6 dígitos,
 * e um cliente que não o conhecesse mostrava o nome técnico pelo ecrã.
 *
 * O `retry_after` é o que separa as duas falhas: «código errado» é um erro de
 * escrita, «demasiadas tentativas» é o PC a dizer para parar. A mesma frase
 * para as duas fazia o utilizador reescrever o código certo e voltar a bater
 * no bloqueio — e a culpar o teclado pelo que é um limite do PC.
 */
export function authErrorMessage(
  error: unknown,
  retryAfter?: unknown
): string {
  const segundos = Math.max(1, Math.ceil(Number(retryAfter) || 0));
  if (error === 'auth_locked') {
    return `Demasiadas tentativas. Espera ${segundos} s e tenta outra vez.`;
  }
  if (error === 'auth_required') {
    return 'Código recusado. Confirma os 6 dígitos no PC (podem ter mudado).';
  }
  return String(error || 'Auth falhou.');
}