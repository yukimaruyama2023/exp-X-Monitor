#!/bin/bash

# CPUs to allow
CPUS="0-4"

# IRQ ranges for enp7s0f0np0 (149-156) and enp7s0f1np1 (172-179)
IRQS=(149 150 151 152 153 154 155 156 172 173 174 175 176 177 178 179)

echo "Setting NIC IRQ affinity to CPUs: $CPUS"
echo

for IRQ in "${IRQS[@]}"; do
  FILE="/proc/irq/${IRQ}/smp_affinity_list"

  if [[ -f "$FILE" ]]; then
    echo "IRQ $IRQ → CPUs $CPUS"
    echo "$CPUS" | sudo tee "$FILE" >/dev/null
  else
    echo "WARNING: $FILE not found"
  fi
done

echo
echo "Done."
