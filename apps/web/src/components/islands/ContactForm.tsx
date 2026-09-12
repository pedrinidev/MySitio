/**
 * Formulario de contacto.
 *
 * La validación del cliente refleja **exactamente** la del servidor
 * (`modules/contact/serializers.py`). Si divergen, el visitante rellena todo,
 * pulsa enviar y recibe un error que el formulario nunca le anticipó — la
 * peor experiencia posible en el único punto del sitio donde alguien intenta
 * contactarte.
 *
 * La validación del cliente es cortesía; la que cuenta es la del servidor.
 */

import { useEffect, useRef, useState } from 'react';
import type { ComponentProps } from 'react';
import { sendContactMessage } from '../../lib/api';
import type { Dictionary } from '../../lib/i18n';
import type { Language } from '../../lib/types';

interface Props {
  lang: Language;
  dict: Dictionary;
}

type Status = 'idle' | 'sending' | 'sent' | 'error';

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

export default function ContactForm({ lang, dict }: Props) {
  const [status, setStatus] = useState<Status>('idle');
  const [errors, setErrors] = useState<Record<string, string>>({});
  // Marca de tiempo del montaje: sirve para medir cuánto tardó en enviarse.
  const mountedAt = useRef(Date.now());

  useEffect(() => {
    mountedAt.current = Date.now();
  }, []);

  function validate(values: Record<string, string>): Record<string, string> {
    const found: Record<string, string> = {};
    if (values.name.trim().length < 2) found.name = dict.contact.required;
    if (!EMAIL_PATTERN.test(values.email.trim())) found.email = dict.contact.invalidEmail;
    if (values.subject.trim().length < 3) found.subject = dict.contact.tooShort;
    if (values.message.trim().length < 10) found.message = dict.contact.tooShort;
    return found;
  }

  // El tipo se deriva del propio <form> en vez de nombrar FormEvent, que
  // @types/react 19 marca como obsoleto. Así el tipo sigue al de React
  // sin que haya que perseguir cambios de nomenclatura.
  const handleSubmit: NonNullable<ComponentProps<'form'>['onSubmit']> = async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);

    const values = {
      name: String(data.get('name') ?? ''),
      email: String(data.get('email') ?? ''),
      subject: String(data.get('subject') ?? ''),
      message: String(data.get('message') ?? ''),
    };

    const found = validate(values);
    setErrors(found);
    if (Object.keys(found).length > 0) return;

    setStatus('sending');

    const { error } = await sendContactMessage({
      ...values,
      locale: lang,
      // Campo señuelo: si un bot lo rellenó, el servidor lo marcará como spam.
      website: String(data.get('website') ?? ''),
      elapsed_ms: Date.now() - mountedAt.current,
    });

    if (error) {
      setStatus('error');
      return;
    }
    setStatus('sent');
    form.reset();
  };

  if (status === 'sent') {
    return (
      <div className="form-success" role="status">
        <svg viewBox="0 0 24 24" aria-hidden="true" className="success-icon">
          <path
            d="M20 6L9 17l-5-5"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
        <p>{dict.contact.success}</p>
      </div>
    );
  }

  return (
    <form className="contact-form" onSubmit={handleSubmit} noValidate>
      <div className="field">
        <label htmlFor="name">{dict.contact.name}</label>
        <input
          id="name"
          name="name"
          type="text"
          required
          autoComplete="name"
          aria-invalid={!!errors.name}
        />
        {errors.name && <p className="field-error">{errors.name}</p>}
      </div>

      <div className="field">
        <label htmlFor="email">{dict.contact.email}</label>
        <input
          id="email"
          name="email"
          type="email"
          required
          autoComplete="email"
          aria-invalid={!!errors.email}
        />
        {errors.email && <p className="field-error">{errors.email}</p>}
      </div>

      <div className="field">
        <label htmlFor="subject">{dict.contact.subject}</label>
        <input id="subject" name="subject" type="text" required aria-invalid={!!errors.subject} />
        {errors.subject && <p className="field-error">{errors.subject}</p>}
      </div>

      <div className="field">
        <label htmlFor="message">{dict.contact.message}</label>
        <textarea id="message" name="message" rows={6} required aria-invalid={!!errors.message} />
        {errors.message && <p className="field-error">{errors.message}</p>}
      </div>

      {/* Honeypot. Se oculta con CSS y se saca del orden de tabulación y del
          árbol de accesibilidad: invisible para una persona (incluida quien
          use lector de pantalla), visible para un bot que lee el DOM. */}
      <div className="honeypot" aria-hidden="true">
        <label htmlFor="website">No completar este campo</label>
        <input id="website" name="website" type="text" tabIndex={-1} autoComplete="off" />
      </div>

      <button type="submit" className="submit" disabled={status === 'sending'}>
        {status === 'sending' ? dict.contact.sending : dict.contact.send}
      </button>

      {status === 'error' && (
        <p className="form-error" role="alert">
          {dict.contact.error}
        </p>
      )}
    </form>
  );
}
